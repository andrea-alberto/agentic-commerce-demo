# Copyright 2026 UCP Authors / GDG DevFest Milano 2026
"""Agent definition and tools for Milano Centrale Travel Retail."""

import logging
from typing import Any
from a2a.types import TaskState
from a2a.utils import get_message_text
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from ucp_sdk.models.schemas.shopping.types.buyer import Buyer
from ucp_sdk.models.schemas.shopping.types.postal_address import PostalAddress

from .a2a_extensions import UcpExtension
from .constants import (
    ADK_EXTENSIONS_STATE_KEY,
    ADK_LATEST_TOOL_RESULT,
    ADK_PAYMENT_STATE,
    ADK_UCP_METADATA_STATE,
    ADK_USER_CHECKOUT_ID,
    UCP_CHECKOUT_KEY,
    UCP_PAYMENT_DATA_KEY,
    UCP_RISK_SIGNALS_KEY,
)
from .payment_processor import MockPaymentProcessor
from .store import RetailStore


store = RetailStore()
mpp = MockPaymentProcessor()


def _create_error_response(message: str) -> dict:
    return {"message": message, "status": "error"}


def _get_current_checkout_id(tool_context: ToolContext) -> str | None:
    return tool_context.state.get(ADK_USER_CHECKOUT_ID)


def search_shopping_catalog(tool_context: ToolContext, query: str = "") -> dict:
    """Search products in the Milano Centrale Travel Retail catalog.

    Args:
        tool_context: The tool context for the current request.
        query: Search keywords (e.g., 'caffe', 'panino', 'powerbank', 'caldo', 'freddo').
    """
    try:
        product_results = store.search_products(query)
        return {"a2a.product_results": product_results.model_dump(mode="json")}
    except Exception:
        logging.exception("Error searching travel retail catalog")
        return _create_error_response(
            "Si è verificato un errore nella ricerca del catalogo. Riprova più tardi."
        )


def add_to_checkout(
    tool_context: ToolContext, product_id: str, quantity: int = 1
) -> dict:
    """Add a product to the travel checkout session.

    Args:
        tool_context: The tool context for the current request.
        product_id: The ID or SKU of the product to add.
        quantity: Number of items (defaults to 1).
    """
    checkout_id = tool_context.state.get(ADK_USER_CHECKOUT_ID)
    ucp_metadata = tool_context.state.get(ADK_UCP_METADATA_STATE)

    if not ucp_metadata:
        return _create_error_response("Errore nella generazione dei metadati UCP.")

    try:
        checkout = store.add_to_checkout(
            ucp_metadata, product_id, quantity, checkout_id
        )
        if not checkout_id:
            tool_context.state[ADK_USER_CHECKOUT_ID] = checkout.id

        auth_email = tool_context.state.get("authenticated_user_email")
        auth_name = tool_context.state.get("authenticated_user_name")
        if auth_email and not checkout.buyer:
            checkout.buyer = Buyer(email=auth_email, first_name=auth_name or "")

        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError as e:
        return _create_error_response(str(e))
    except Exception:
        logging.exception("Error adding product to checkout")
        return _create_error_response("Errore durante l'aggiunta al carrello.")


def remove_from_checkout(tool_context: ToolContext, product_id: str) -> dict:
    """Remove a product from the checkout session.

    Args:
        tool_context: The tool context.
        product_id: The product ID to remove.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    try:
        return {
            UCP_CHECKOUT_KEY: (
                store.remove_from_checkout(checkout_id, product_id).model_dump(
                    mode="json"
                )
            ),
            "status": "success",
        }
    except ValueError as e:
        return _create_error_response(str(e))


def update_checkout(tool_context: ToolContext, product_id: str, quantity: int) -> dict:
    """Update quantity of an item in the checkout session.

    Args:
        tool_context: The tool context.
        product_id: The product ID to update.
        quantity: New quantity.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    try:
        return {
            UCP_CHECKOUT_KEY: (
                store.update_checkout(checkout_id, product_id, quantity).model_dump(
                    mode="json"
                )
            ),
            "status": "success",
        }
    except ValueError as e:
        return _create_error_response(str(e))


def get_checkout(tool_context: ToolContext) -> dict:
    """Retrieve current checkout status and totals."""
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    checkout = store.get_checkout(checkout_id)
    if checkout is None:
        return _create_error_response("Carrello non trovato.")

    return {
        UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
        "status": "success",
    }


def get_available_fulfillment_slots(tool_context: ToolContext, option_id: str = "all") -> dict:
    """Get available scheduled delivery or pickup time slots.

    Args:
        tool_context: Tool context.
        option_id: 'pickup_locker' (multipli di 10 min), 'pickup_express' (intervalli di 5 min), o 'all'.
    """
    slots = store.get_available_slots(option_id)
    return {"a2a.time_slots": slots, "status": "success"}


def select_delivery_method(
    tool_context: ToolContext, option_id: str, slot_time: str | None = None
) -> dict:
    """Select fulfillment method: 'pickup_express', 'pickup_locker', or 'in_seat_train'.

    Args:
        tool_context: Tool context.
        option_id: 'pickup_express' (Bistrot/Tavolo, 5 min), 'pickup_locker' (Smart Locker, multipli di 10 min, solo freddi), o 'in_seat_train' (Consegna al posto, 1 min max attesa, €6.50).
        slot_time: Optional preferred time or slot (e.g., '14:20' o '17:15').
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    try:
        checkout = store.select_fulfillment_option(
            checkout_id, option_id, slot_time=slot_time
        )
        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError as e:
        return _create_error_response(str(e))


def set_train_delivery_details(
    tool_context: ToolContext,
    train_number: str,
    carriage: str,
    seat: str,
    delivery_time: str | None = None,
    platform: str | None = None,
    passenger_name: str = "Passeggero",
    email: str = "viaggiatore@trenitalia.example.it",
) -> dict:
    """Configure in-seat train delivery details with train number, carriage, seat, platform and arrival time.

    Args:
        tool_context: Tool context.
        train_number: Train code, e.g., 'Frecciarossa 9540' or 'Italo 9924'.
        carriage: Carriage/Vagone number, e.g., 'Carrozza 4'.
        seat: Seat number, e.g., '12D' or '5A'.
        delivery_time: Precise delivery/arrival time, e.g., '17:15'. The courier wait window is strictly 1 minute.
        platform: Platform/Binario, e.g., 'Binario 14'.
        passenger_name: Passenger name.
        email: Contact email for order updates.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    auth_email = tool_context.state.get("authenticated_user_email")
    auth_name = tool_context.state.get("authenticated_user_name")
    if (not email or email == "viaggiatore@trenitalia.example.it") and auth_email:
        email = auth_email
    if (not passenger_name or passenger_name == "Passeggero") and auth_name:
        passenger_name = auth_name

    try:
        checkout = store.set_train_delivery(
            checkout_id=checkout_id,
            train_number=train_number,
            carriage=carriage,
            seat=seat,
            delivery_time=delivery_time,
            platform=platform,
            passenger_name=passenger_name,
            email=email,
        )
        return start_payment(tool_context)
    except Exception as e:
        logging.exception("Error configuring train delivery")
        return _create_error_response(f"Errore nella configurazione della consegna al treno: {str(e)}")


def set_table_service_details(
    tool_context: ToolContext,
    table_number: str = "Al Banco",
    service_time: str | None = None,
    customer_name: str = "Cliente Bistrot",
    email: str = "cliente@devfest.example.it",
) -> dict:
    """Configure table service or express counter pickup with a 5-minute window.

    Args:
        tool_context: Tool context.
        table_number: 'Al Banco' per ritiro/consegna al bancone/banco, oppure 'Tavolo X' (es. 'Tavolo 1', 'Tavolo 3', 'Tavolo 5', 'Tavolo 12'). Default 'Al Banco'.
        service_time: Desired time slot (e.g., '16:55'). Preparation window is strictly 5 minutes.
        customer_name: Customer name.
        email: Contact email.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    auth_email = tool_context.state.get("authenticated_user_email")
    auth_name = tool_context.state.get("authenticated_user_name")
    if (not email or email == "cliente@devfest.example.it") and auth_email:
        email = auth_email
    if (not customer_name or customer_name == "Cliente Bistrot") and auth_name:
        customer_name = auth_name

    try:
        checkout = store.set_table_service(
            checkout_id=checkout_id,
            table_number=table_number,
            service_time=service_time,
            customer_name=customer_name,
            email=email,
        )
        return start_payment(tool_context)
    except Exception as e:
        logging.exception("Error configuring table service")
        return _create_error_response(f"Errore nella configurazione del servizio: {str(e)}")


def set_locker_pickup_details(
    tool_context: ToolContext,
    slot_time: str | None = None,
    pin_code: str = "8492",
    customer_name: str = "Cliente Locker",
    email: str = "cliente@devfest.example.it",
) -> dict:
    """Configure Smart Locker pickup at intervals strictly starting at multiples of 10 minutes.

    Args:
        tool_context: Tool context.
        slot_time: Preferred slot start, strictly at multiples of 10 minutes (e.g., '17:10', '17:20', '17:30').
        pin_code: Contactless PIN for locker unlocking.
        customer_name: Customer name.
        email: Contact email.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    auth_email = tool_context.state.get("authenticated_user_email")
    auth_name = tool_context.state.get("authenticated_user_name")
    if (not email or email == "cliente@devfest.example.it") and auth_email:
        email = auth_email
    if (not customer_name or customer_name == "Cliente Locker") and auth_name:
        customer_name = auth_name

    try:
        checkout = store.set_locker_pickup(
            checkout_id=checkout_id,
            slot_time=slot_time,
            pin_code=pin_code,
            customer_name=customer_name,
            email=email,
        )
        return start_payment(tool_context)
    except ValueError as e:
        return _create_error_response(str(e))
    except Exception as e:
        logging.exception("Error configuring locker pickup")
        return _create_error_response(f"Errore nella configurazione dello Smart Locker: {str(e)}")


def update_customer_details(
    tool_context: ToolContext,
    email: str,
    first_name: str | None = None,
    last_name: str | None = None,
    street_address: str | None = "Stazione Milano Centrale, Piazza Duca d'Aosta 1",
    address_locality: str = "Milano",
    address_region: str = "MI",
    postal_code: str = "20124",
    address_country: str | None = "IT",
    extended_address: str | None = None,
) -> dict:
    """Set or update buyer contact and delivery information for the UCP checkout session.

    Args:
        tool_context: Tool context.
        email: Buyer email address (MANDATORY for order confirmation, PIN codes, and receipts).
        first_name: Buyer first name (OPTIONAL).
        last_name: Buyer last name (OPTIONAL).
        street_address: Station address or reference location (OPTIONAL, default Piazza Duca d'Aosta 1).
        address_locality: City locality (default 'Milano').
        address_region: Region code (default 'MI').
        postal_code: Postal code (default '20124').
        address_country: Country ISO code (default 'IT').
        extended_address: Additional delivery notes or table/box reference (OPTIONAL).
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    address = PostalAddress(
        street_address=street_address or "Stazione Milano Centrale, Piazza Duca d'Aosta 1",
        extended_address=extended_address,
        address_locality=address_locality,
        address_region=address_region,
        address_country=address_country or "IT",
        postal_code=postal_code,
        first_name=first_name or "",
        last_name=last_name or "",
    )

    checkout = store.add_delivery_address(checkout_id, address)
    if email:
        checkout.buyer = Buyer(
            email=email,
            first_name=first_name or "",
            last_name=last_name or "",
        )

    return start_payment(tool_context)


def start_payment(tool_context: ToolContext) -> dict:
    """Verify ready_for_complete status and initiate payment."""
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    checkout = store.get_checkout(checkout_id)
    if checkout and not checkout.buyer:
        auth_email = tool_context.state.get("authenticated_user_email")
        auth_name = tool_context.state.get("authenticated_user_name")
        if auth_email:
            checkout.buyer = Buyer(email=auth_email, first_name=auth_name or "")

    result = store.start_payment(checkout_id)
    if isinstance(result, str):
        return {"message": result, "status": "requires_more_info"}
    else:
        tool_context.actions.skip_summarization = True
        return {
            UCP_CHECKOUT_KEY: result.model_dump(mode="json"),
            "status": "success",
        }


async def complete_checkout(tool_context: ToolContext) -> dict:
    """Process payment mandate and complete order."""
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("Nessun carrello attivo.")

    checkout = store.get_checkout(checkout_id)
    if checkout is None:
        return _create_error_response("Carrello non trovato.")

    payment_data: dict[str, Any] = tool_context.state.get(ADK_PAYMENT_STATE)
    if payment_data is None:
        return {
            "message": "Dati di pagamento mancanti. Clicca su 'Complete Payment' per confermare.",
            "status": "requires_more_info",
        }

    try:
        task = mpp.process_payment(
            payment_data[UCP_PAYMENT_DATA_KEY],
            payment_data[UCP_RISK_SIGNALS_KEY],
        )

        if task is None:
            return _create_error_response("Nessuna risposta dal Payment Processor")

        if task.status is not None and task.status.state == TaskState.completed:
            payment_instrument = payment_data.get(UCP_PAYMENT_DATA_KEY)
            checkout.payment.selected_instrument_id = payment_instrument.root.id
            checkout.payment.instruments = [payment_instrument]

            response = store.place_order(checkout_id)
            tool_context.state[ADK_USER_CHECKOUT_ID] = None
            return {
                UCP_CHECKOUT_KEY: response.model_dump(mode="json"),
                "status": "success",
            }
        else:
            return _create_error_response(get_message_text(task.status.message))
    except Exception:
        logging.exception("Error completing checkout")
        return _create_error_response("Errore durante il completamento dell'ordine.")


def after_tool_modifier(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> dict | None:
    extensions = tool_context.state.get(ADK_EXTENSIONS_STATE_KEY, [])
    ucp_response_keys = [UCP_CHECKOUT_KEY, "a2a.product_results"]
    if UcpExtension.URI in extensions and any(
        key in tool_response for key in ucp_response_keys
    ):
        tool_context.state[ADK_LATEST_TOOL_RESULT] = tool_response
    return None


def modify_output_after_agent(
    callback_context: CallbackContext,
) -> types.Content | None:
    latest_result = callback_context.state.get(ADK_LATEST_TOOL_RESULT)
    if latest_result:
        return types.Content(
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        response={"result": latest_result}
                    )
                )
            ],
            role="model",
        )
    return None


AGENT_INSTRUCTION = (
    "Sei l'assistente ufficiale di shopping e travel concierge della Stazione di Milano Centrale per il GDG DevFest 2026.\n"
    "Aiuti i passeggeri a ordinare cibi caldi o freddi, bevande ed accessori tecnologici prima di salire sul treno o mentre sono a bordo.\n\n"
    "REGOLE CRITICHE DI FULFILLMENT E BUSINESS:\n"
    "0. REGOLA DEL PREAVVISO MINIMO DI 30 MINUTI:\n"
    "   - Sia per lo SMART LOCKER sia per la CONSEGNA AL POSTO TRENO/BINARIO è TASSATIVO un PREAVVISO DI ALMENO 30 MINUTI rispetto all'ora attuale.\n"
    "   - Se il passeggero ha meno di 30 minuti prima della partenza del treno o del ritiro, spiega chiaramente che per motivi operativi di sicurezza e preparazione serve un preavviso di 30 min, e proponi come alternativa immediata il RITIRO EXPRESS AL BANCO (Binario 12), pronto in soli 5 minuti!\n\n"
    "1. RITIRO SMART LOCKER (Piano Interrato):\n"
    "   - PREAVVISO MINIMO: almeno 30 minuti dall'ordine. Gli slot partono rigorosamente ai MULTIPLI DI 10 MINUTI (:00, :10, :20, :30, :40, :50) con durata di 10 minuti.\n"
    "   - Valido SOLO ed ESCLUSIVAMENTE per alimenti freddi, bibite e prodotti tecnologici (panini freddi, insalate, powerbank, caricatori).\n"
    "   - Sblocco con codice PIN contactless fornito all'ordine. Gratuito (€0.00).\n"
    "   - DIVIETO ASSOLUTO PER PRODOTTI CALDI: se il carrello contiene caffè espresso, cappuccino o toast caldi, rifiuta cortesemente spiegando le norme di qualità e sicurezza alimentare e proponi il Ritiro Express al Banco o la Consegna al Posto Treno.\n"
    "   - Invoca lo strumento `set_locker_pickup_details` (o `select_delivery_method`) specificando lo `slot_time` desiderato.\n\n"
    "2. CONSEGNA AL POSTO TRENO (Frecciarossa / Italo / Binario):\n"
    "   - PREAVVISO MINIMO: almeno 30 minuti prima dell'arrivo/fermata del treno.\n"
    "   - Consegna a bordo treno diretta alla carrozza e al posto del viaggiatore mentre il treno è fermo al binario.\n"
    "   - FINESTRA DI MASSIMA PRECISIONE: ATTESA MASSIMA DEL FATTORINO DI 1 MINUTO durante la sosta del treno (es. finestra 17:45–17:46)!\n"
    "   - Richiede: Numero Treno (es. 'Frecciarossa 9540'), Carrozza (es. 'Carrozza 4'), Posto (es. '12D'), Orario di consegna/arrivo al binario (es. '17:45') e Binario (es. 'Binario 14').\n"
    "   - Supplemento di servizio: €6.50 (incluso nei totali del carrello).\n"
    "   - Se l'utente chiede la consegna al treno, chiedi i dati mancanti oppure invoca direttamente `set_train_delivery_details`.\n\n"
    "3. RITIRO AL BANCO O SERVIZIO AL TAVOLO (Bistrot Binario 12):\n"
    "   - Ritiro express al banco/bancone oppure servizio al tavolo presso il Bistrot Binario 12.\n"
    "   - NESSUN PREAVVISO RICHIESTO: pronto in soli 5 minuti!\n"
    "   - Gratuito (€0.00). Disponibile per TUTTI i prodotti (caldi e freddi).\n"
    "   - Finestra temporale: INTERVALLO DI 5 MINUTI per preparazione e servizio (es. 16:30–16:35).\n"
    "   - Accetta: 'Al Banco' (se l'utente chiede consegna/ritiro al banco o al bancone, asporto o desk rapido) oppure Numero Tavolo (es. 'Tavolo 5'). Se l'utente non specifica, usa 'Al Banco'.\n"
    "   - Invoca `set_table_service_details` impostando table_number='Al Banco' o 'Tavolo X' e orario desiderato.\n\n"
    "REGOLE ANAGRAFICA ACQUIRENTE (BUYER):\n"
    "- L'unico dato tassativo e obbligatorio per procedere con il pagamento e inviare le notifiche dell'ordine è l'email (es. alex.traveler@example.com).\n"
    "- Nome e cognome dell'acquirente sono OPZIONALI: se l'utente fornisce solo l'email o non indica il nome, non insistere e procedi subito.\n"
    "REGOLE CRITICHE PER RICHIESTE MULTI-ARTICOLO:\n"
    "- Se l'utente chiede più prodotti nella stessa richiesta (es. 'un espresso doppio caldo e una brioche al pistacchio', oppure 'un panino e un'acqua', oppure 'un caffè, una brioche e un caricatore 65W'), DEVI AGGIUNGERE TUTTI GLI ARTICOLI AL CARRELLO!\n"
    "- Invoca `add_to_checkout` per CIASCUN prodotto richiesto (es. `add_to_checkout(product_id='CAFFE-001')` e `add_to_checkout(product_id='PAST-002')`). Non fermarti al primo articolo, il carrello finale deve contenere TUTTI gli articoli richiesti dal viaggiatore.\n"
    "- Per 'espresso doppio caldo e una brioche al pistacchio': aggiungi sia `CAFFE-001` (Espresso Doppio Illy Caldo) sia `PAST-002` (Brioche Artigianale al Pistacchio di Bronte). Non aggiungere solo il caffè!\n"
    "- Se l'utente menziona già il ritiro al banco ('da ritirare al banco prima della partenza'), oltre ad aggiungere i prodotti imposta subito `set_table_service_details` con table_number='Al Banco'.\n\n"
    "REGOLE DI INTERAZIONE:\n"
    "- Ogni volta che l'utente chiede cosa c'è disponibile, cosa può mangiare o bere, o cerca prodotti, invoca SEMPRE il tool `search_shopping_catalog` per visualizzare le card strutturate dei prodotti.\n"
    "- Se l'utente chiede di consultare gli slot orari disponibili per il locker o il tavolo, invoca `get_available_fulfillment_slots`.\n"
    "- Se l'utente chiede di aggiungere, modificare o rimuovere prodotti dal carrello, usa i rispettivi tool (`add_to_checkout`, `remove_from_checkout`, `update_checkout`).\n"
    "- Rispondi in italiano in modo cortese, veloce, dinamico e proattivo, perfetto per un viaggiatore in stazione centrale."
)

root_agent = Agent(
    name="milano_travel_retail_agent",
    model="gemini-3.8-flash",
    description="Agent per shopping e delivery rapido alla Stazione di Milano Centrale",
    instruction=AGENT_INSTRUCTION,
    tools=[
        search_shopping_catalog,
        add_to_checkout,
        remove_from_checkout,
        update_checkout,
        get_checkout,
        get_available_fulfillment_slots,
        select_delivery_method,
        set_train_delivery_details,
        set_table_service_details,
        set_locker_pickup_details,
        update_customer_details,
        start_payment,
        complete_checkout,
    ],
    after_tool_callback=after_tool_modifier,
    after_agent_callback=modify_output_after_agent,
)
