# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Web MCP Server for Milano Centrale Travel Store.

Exposes store catalog, cart, fulfillment selection, and checkout as standard
Model Context Protocol (MCP) tools for autonomous Shopper Agents.
Delegates domain and cart logic to the agnostic CatalogService.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .catalog_service import (
    CatalogService,
    catalog_service,
    MIN_LEAD_TIME_TRAIN_MINUTES,
    MIN_LEAD_TIME_LOCKER_MINUTES,
    TRAIN_DELIVERY_FEE_CENTS,
)

logger = logging.getLogger("travel_retail_agent.mcp")

# Expose catalog_service as mcp_store for backward compatibility
mcp_store = catalog_service
WebMcpStoreService = CatalogService


# MCP Tool Schemas Specification (conforming to Model Context Protocol)
MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_catalog",
        "description": (
            "Cerca alimenti caldi/freddi, bevande ed accessori nel catalogo di Milano Centrale. "
            "Restituisce una lista sintetica con id, nome, prezzo, compatibilità Smart Locker (locker_compatible: true/false). "
            "IMPORTANTE PER ACQUISTI MULTIPLI: Cerca un solo articolo alla volta. "
            "Se l'utente richiede più articoli non correlati (es. 'spremuta' e 'panino vegano'), non combinare i termini: "
            "cerca prima il primo articolo, aggiungilo subito al carrello con add_to_cart, e solo dopo cerca il secondo articolo. "
            "Esempi query: 'spremuta', 'panino vegano', 'vegano', 'caffe', 'croissant'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Parola chiave singola (es. 'spremuta', 'panino vegano', 'caffe', 'croissant').",
                },
                "category": {
                    "type": "string",
                    "description": "Categoria facoltativa per filtrare i risultati (es. 'all', 'cold', 'hot', 'tech').",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_product_details",
        "description": "Recupera la scheda tecnica completa, valori nutrizionali, allergeni e compatibilità di un articolo tramite product_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID dell'articolo (es. 'BEV-007', 'VEG-012', 'CAFFE-001', 'PANIN-004').",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "create_cart",
        "description": "Inizializza una nuova sessione di carrello della spesa per il viaggiatore. Restituisce cart_id.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "add_to_cart",
        "description": (
            "Aggiunge uno o più pezzi di un prodotto al carrello della spesa. "
            "REGOLA D'ORO: Chiama questo tool subito dopo aver individuato l'ID del prodotto con search_catalog (es. BEV-007, VEG-012), "
            "PRIMA di procedere alla ricerca del prossimo articolo."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "string",
                    "description": "ID del carrello ottenuto con create_cart.",
                },
                "product_id": {
                    "type": "string",
                    "description": "ID del prodotto da aggiungere (es. 'BEV-007', 'VEG-012').",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Numero di pezzi da aggiungere (default 1).",
                    "default": 1,
                },
            },
            "required": ["cart_id", "product_id"],
        },
    },
    {
        "name": "remove_from_cart",
        "description": "Rimuove un articolo o ne diminuisce la quantità nel carrello.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "string",
                    "description": "ID del carrello.",
                },
                "product_id": {
                    "type": "string",
                    "description": "ID del prodotto da rimuovere.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Numero di pezzi da rimuovere (omettere per rimuovere tutto).",
                },
            },
            "required": ["cart_id", "product_id"],
        },
    },
    {
        "name": "configure_fulfillment",
        "description": (
            "Imposta la modalità di consegna/ritiro a Milano Centrale:\n"
            "- 'pickup': Ritiro rapido al Banco Bistrot (Binario 12, piano binari). Tempo min: 5 min.\n"
            "- 'locker': Smart Locker Refrigerato (Piazza Duca d'Aosta). Tempo min: 30 min. NON supporta bevande calde non sigillate!\n"
            "- 'train': Consegna al posto a bordo treno Frecciarossa/Italo. Tempo min: 30 min. Richiede train_number, coach, seat."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "string",
                    "description": "ID del carrello.",
                },
                "method": {
                    "type": "string",
                    "enum": ["pickup", "locker", "train"],
                    "description": "Metodo di fulfillment.",
                },
                "details": {
                    "type": "object",
                    "description": "Dettagli specifici per il fulfillment.",
                    "properties": {
                        "pickup_time": {
                            "type": "string",
                            "description": "Orario previsto di ritiro o consegna (formato HH:MM, es. '15:45').",
                        },
                        "train_number": {
                            "type": "string",
                            "description": "Numero del treno per consegna a bordo (es. 'FR 9540', 'IT 9924').",
                        },
                        "coach": {
                            "type": "string",
                            "description": "Carrozza del treno (es. 'Carrozza 4').",
                        },
                        "seat": {
                            "type": "string",
                            "description": "Numero del posto (es. 'Posto 12A').",
                        },
                    },
                },
            },
            "required": ["cart_id", "method"],
        },
    },
    {
        "name": "checkout_cart",
        "description": "Esegue il checkout finale del carrello, formalizza l'ordine commerciale ed invia l'ordine al sistema di preparazione della stazione (BOPIS).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cart_id": {
                    "type": "string",
                    "description": "ID del carrello configurato.",
                },
                "buyer_name": {
                    "type": "string",
                    "description": "Nome del viaggiatore acquirente.",
                    "default": "Viaggiatore MCP",
                },
                "buyer_email": {
                    "type": "string",
                    "description": "Email per notifiche di tracciamento.",
                    "default": "shopper.mcp@devfest.example.it",
                },
                "payment_method": {
                    "type": "string",
                    "enum": ["gpay", "card", "ap2"],
                    "description": "Metodo di pagamento scelto: 'gpay' (Google Pay), 'card' (Carta di Credito), 'ap2' (Mandato AP2 Pre-Approvato).",
                    "default": "gpay",
                },
            },
            "required": ["cart_id"],
        },
    },
]


def execute_mcp_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a single MCP tool by name and arguments."""
    try:
        if name == "search_catalog":
            query = arguments.get("query", "")
            category = arguments.get("category", "")
            items = mcp_store.search_products(query, category)
            return {"results": items, "count": len(items)}

        elif name == "get_product_details":
            product_id = arguments["product_id"]
            p = mcp_store.get_product(product_id)
            if not p:
                return {"error": f"Prodotto {product_id} non trovato"}
            return {"product": p}

        elif name == "create_cart":
            cart = mcp_store.create_cart()
            return {"cart": cart}

        elif name == "add_to_cart":
            cart_id = arguments["cart_id"]
            product_id = arguments["product_id"]
            quantity = int(arguments.get("quantity", 1))
            updated_cart = mcp_store.add_to_cart(cart_id, product_id, quantity)
            return {
                "message": f"Articolo {product_id} (x{quantity}) aggiunto al carrello {cart_id}",
                "cart": updated_cart,
            }

        elif name == "remove_from_cart":
            cart_id = arguments["cart_id"]
            product_id = arguments["product_id"]
            quantity = arguments.get("quantity", 1)
            if quantity is not None:
                quantity = int(quantity)
            updated_cart = mcp_store.remove_from_cart(cart_id, product_id, quantity)
            return {
                "message": f"Articolo {product_id} rimosso dal carrello {cart_id}",
                "cart": updated_cart,
            }

        elif name == "configure_fulfillment":
            cart_id = arguments["cart_id"]
            method = arguments["method"]
            details = arguments.get("details", {})
            updated_cart = mcp_store.configure_fulfillment(cart_id, method, details)
            return {
                "message": f"Fulfillment '{method}' configurato con successo",
                "cart": updated_cart,
            }

        elif name == "checkout_cart":
            cart_id = arguments["cart_id"]
            buyer_name = arguments.get("buyer_name", "Viaggiatore MCP")
            buyer_email = arguments.get("buyer_email", "shopper.mcp@devfest.example.it")
            payment_method = arguments.get("payment_method", "gpay")
            order_res = mcp_store.checkout_cart(cart_id, buyer_name, buyer_email, payment_method)
            return order_res

        else:
            return {"error": f"Tool MCP '{name}' sconosciuto"}
    except Exception as e:
        logger.warning("Errore esecuzione tool MCP '%s': %s", name, e)
        return {"error": str(e), "status": "failed"}


def handle_mcp_jsonrpc(req: dict[str, Any]) -> dict[str, Any]:
    """Dispatch MCP standard JSON-RPC 2.0 messages."""
    req_id = req.get("id", 1)
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "milano-centrale-travel-mcp",
                    "version": "1.0.0",
                    "description": "Storefront MCP Server per la Stazione di Milano Centrale (GDG DevFest 2026)",
                },
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS,
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result_content = execute_mcp_tool(tool_name, arguments)
        is_error = "error" in result_content
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result_content, ensure_ascii=False, indent=2),
                    }
                ],
                "isError": is_error,
            },
        }

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Metodo MCP '{method}' non supportato",
            },
        }
