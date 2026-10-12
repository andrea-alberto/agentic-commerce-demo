# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Autonomous Shopper Agent powered by Gemini using Model Context Protocol (MCP) tools."""

from datetime import datetime, timezone, timedelta
import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from google import genai
from google.genai import types

from .mcp_server import execute_mcp_tool, MCP_TOOLS

logger = logging.getLogger("travel_retail_agent.shopper_agent")

SHOPPER_SYSTEM_INSTRUCTION = """\
Sei un Personal Shopper Concierge per il passeggero in transito alla Stazione di Milano Centrale per il GDG DevFest 2026.
Il tuo compito è completare gli acquisti per conto dell'utente interagendo autonomamente con lo Storefront E-Commerce
della stazione tramite i Tool del Model Context Protocol (MCP) conformi allo standard UCP (Universal Commerce Protocol).

LINEE GUIDA PER L'ESECUZIONE CON TOOL MCP E PROTOCOLLO UCP:
1. Cerca i prodotti adatti usando `search_catalog` in base ai desideri del viaggiatore.
   Ogni prodotto espone le modalità di fulfillment ammesse (es. i prodotti caldi non consentono il locker).
2. Inizializza un carrello della spesa chiamando `create_cart`.
3. Aggiungi gli articoli trovati usando `add_to_cart` con il `cart_id` generato.
4. Per la consegna o ritiro (`configure_fulfillment`):
   - ISPEZIONA LE OPZIONI DI FULFILLMENT RESTITUITE DAL CARRELLO: il BOPIS Engine della stazione calcola dinamicamente le `available_fulfillment_options` in base agli articoli presenti nel carrello.
   - Scegli tra le opzioni effettivamente disponibili restituite dal carrello:
     * 'pickup' (Standard UCP per ritiro rapido al banco Bistrot Binario 12, pronto in 5 min, idoneo per tutti i prodotti caldi e freddi).
     * 'pickup_locker' o l'id dello slot discreto disponibile (es. 'pickup_locker_1430' per Smart Locker al piano interrato, contactless con PIN, disponibile solo se presente tra le opzioni del carrello).
     * 'in_seat_train' (Consegna al posto in treno, se richiesta dal passeggero).
   - Se il passeggero richiede una modalità non compatibile con gli articoli scelti (es. locker per un caffè o cibo caldo), seleziona la modalità alternativa valida ('pickup' al banco) spiegando la motivazione all'utente.
5. Finalizza l'acquisto con `checkout_cart` specificando il `cart_id` e i dati dell'acquirente.
6. Fornisci un resoconto finale chiaro, sintetico e professionale al viaggiatore indicando l'ID dell'ordine, i prodotti acquistati, l'orario e la modalità di consegna confermata dal negozio.
"""


class AutonomousShopperAgent:
    """Agent that runs autonomous multi-turn tool loops over MCP."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY mancante!")
        self.client = genai.Client(api_key=self.api_key)

    def _convert_mcp_to_gemini_tools(self) -> list[Any]:
        """Convert MCP tool specifications into Gemini FunctionDeclarations."""
        func_declarations = []
        for tool in MCP_TOOLS:
            schema = tool["inputSchema"]
            # Map json schema properties to types.Schema
            properties = {}
            for prop_name, prop_def in schema.get("properties", {}).items():
                p_type = prop_def.get("type", "string")
                t_enum = types.Type.STRING
                if p_type == "integer":
                    t_enum = types.Type.INTEGER
                elif p_type == "number":
                    t_enum = types.Type.NUMBER
                elif p_type == "boolean":
                    t_enum = types.Type.BOOLEAN
                elif p_type == "object":
                    t_enum = types.Type.OBJECT

                properties[prop_name] = types.Schema(
                    type=t_enum,
                    description=prop_def.get("description", ""),
                    enum=prop_def.get("enum") if "enum" in prop_def else None,
                )

            decl = types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=properties,
                    required=schema.get("required", []),
                ),
            )
            func_declarations.append(decl)
        return [types.Tool(function_declarations=func_declarations)]

    async def run_shopping_mission(
        self,
        prompt: str,
        buyer_name: str = "Viaggiatore MCP",
        buyer_email: str = "shopper.mcp@devfest.example.it",
    ) -> dict[str, Any]:
        """Execute autonomous shopping mission over MCP tools and return full execution trace."""
        logger.info("Avvio Shopping Mission MCP per il prompt: '%s'", prompt)
        gemini_tools = self._convert_mcp_to_gemini_tools()

        now_dt = datetime.now().astimezone()
        context_prompt = (
            f"Orario attuale della Stazione di Milano Centrale: {now_dt.strftime('%H:%M:%S')} (Data: {now_dt.strftime('%d/%m/%Y')}).\n"
            f"Nome acquirente: {buyer_name} ({buyer_email}).\n"
            f"Richiesta viaggiatore: {prompt}"
        )

        chat = self.client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SHOPPER_SYSTEM_INSTRUCTION,
                temperature=0.1,
                tools=gemini_tools,
            ),
        )

        trace_steps: list[dict[str, Any]] = []
        order_confirmed: Optional[dict[str, Any]] = None
        max_iterations = 8
        current_iter = 0

        response = chat.send_message(context_prompt)

        while current_iter < max_iterations:
            current_iter += 1

            # Check if model made function calls
            function_calls = []
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)

            if not function_calls:
                # Finished execution
                break

            # Process function calls
            function_responses = []
            for fc in function_calls:
                fn_name = fc.name
                fn_args = dict(fc.args) if fc.args else {}

                rpc_id = len(trace_steps) + 1
                mcp_req = {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "method": "tools/call",
                    "params": {
                        "name": fn_name,
                        "arguments": fn_args,
                    },
                }

                # Execute MCP tool
                execution_result = execute_mcp_tool(fn_name, fn_args)

                mcp_res = {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(execution_result, ensure_ascii=False),
                            }
                        ],
                        "isError": "error" in execution_result,
                    },
                }

                # Record in trace for live UI inspector
                trace_steps.append({
                    "step": rpc_id,
                    "tool": fn_name,
                    "arguments": fn_args,
                    "result": execution_result,
                    "mcp_request": mcp_req,
                    "mcp_response": mcp_res,
                    "timestamp": datetime.now().astimezone().strftime("%H:%M:%S.%f")[:-3],
                })

                if fn_name == "checkout_cart" and execution_result.get("status") == "confirmed":
                    order_confirmed = execution_result

                function_responses.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": execution_result},
                    )
                )

            # Send tool outputs back to model
            response = chat.send_message(function_responses)

        final_text = response.text or "Missione di acquisto MCP completata con successo."

        return {
            "status": "success" if order_confirmed else "partial",
            "prompt": prompt,
            "steps": trace_steps,
            "total_steps": len(trace_steps),
            "order": order_confirmed,
            "final_answer": final_text,
            "completed_at": datetime.now().astimezone().strftime("%d/%m/%Y %H:%M:%S"),
        }
