#!/usr/bin/env python3
"""
UCP Merchant Middleware on Google Cloud Platform
Diagram as Code generator using the `diagrams` library.

References:
- GDG DevFest Milano 2026: Agentic Commerce across UCP, Web MCP, and Physical Retail
- docs/gcp-ucp-architecture.md
- Demo 3 (Two-Agent A2A Federation) & Demo 4 (UCP Standard REST Binding with RFC 9421)
"""
import os
import sys

from diagrams import Diagram, Cluster, Edge
# GCP Official Icons
from diagrams.gcp.compute import Run
from diagrams.gcp.database import Firestore
from diagrams.gcp.ml import VertexAI
from diagrams.gcp.network import Armor, DNS, LoadBalancing
from diagrams.gcp.security import KeyManagementService, SecretManager
from diagrams.gcp.analytics import Pubsub
from diagrams.gcp.devtools import Tasks
from diagrams.gcp.storage import Storage
# Client & Physical Device Icons
from diagrams.onprem.client import Client, Users
from diagrams.generic.device import Tablet, Mobile
from diagrams.onprem.compute import Server


def generate_architecture_diagram():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ucp_gcp_architecture")

    graph_attr = {
        "fontsize": "24",
        "fontname": "Arial",
        "bgcolor": "white",
        "pad": "0.6",
        "splines": "spline",
        "nodesep": "0.75",
        "ranksep": "0.95",
    }
    node_attr = {
        "fontname": "Arial",
        "fontsize": "11",
    }
    edge_attr = {
        "fontname": "Arial",
        "fontsize": "9",
        "color": "#1a73e8",
    }

    with Diagram(
        "Cloud-Native UCP Merchant Middleware on Google Cloud Platform",
        filename=output_path,
        show=False,
        direction="TB",
        graph_attr=graph_attr,
        node_attr=node_attr,
        edge_attr=edge_attr,
        outformat=["png", "svg"],
    ):
        # 1. EXTERNAL ACTORS & CLIENTS
        with Cluster("External AI Shoppers & Channels"):
            shopper_agent = Mobile("Personal Shopper Agent\n(Gemini 2.5 Flash / Demo 3 & 4)")
            web_shopper = Users("Web MCP Shopper\n(Storefront Demo 2)")
            agentic_network = Client("3rd-Party Agent Networks\n(OpenAI ACP / Agents)")

        # 2. INGRESS & EDGE SECURITY (GCP)
        with Cluster("Ingress & Edge Security Layer (GCP)"):
            dns = DNS("Cloud DNS\nucp.merchant.com")
            armor = Armor("Cloud Armor\n(WAF, DDoS & Rate Limit)")
            api_gw = LoadBalancing("API Gateway / Apigee\n(RFC 9421 ECDSA & Ingress)")

        # 3. SERVERLESS COMPUTE (CLOUD RUN)
        with Cluster("Serverless Compute Tier (Google Cloud Run)"):
            with Cluster("ucp-merchant-service (FastAPI / Starlette)"):
                ucp_core = Run("UCP Core Engine\n• REST (/.well-known, /checkouts)\n• A2A (/a2a/negotiate, /commit)\n• Web MCP Bridge (/mcp/tools)")
                bopis_engine = Run("BOPIS Logistics Engine\n• Thermal Checks (is_hot)\n• 30m Lead Time Rules\n• Seat & Locker Allocator")
                ap2_verifier = Run("AP2 Verifier\n• SD-JWT Verification\n• Hardware FIDO2 Passkeys")

            with Cluster("bopis-websocket-gateway"):
                ws_gw = Run("WebSocket Gateway\n(Managed Real-Time Push)")

        # 4. INTELLIGENCE TIER (VERTEX AI)
        with Cluster("Intelligence Tier (Vertex AI)"):
            gemini = VertexAI("Gemini 2.5 Flash\n• Structured Outputs (Pydantic)\n• Multi-item Combo Bundles\n• Dietary & Context Alignment")

        # 5. DATA PERSISTENCE & SECRETS
        with Cluster("Persistence & Security Tier"):
            firestore = Firestore("Cloud Firestore\n(/catalogs, /checkouts,\n/bopis_orders, /keys)")
            kms = KeyManagementService("Cloud KMS\n(ECDSA-P256 Keys &\nRFC 9421 Verification)")
            secrets = SecretManager("Secret Manager\n(PSP & ERP API Keys)")
            gcs = Storage("Cloud Storage (GCS)\n(UCP Schemas & Media)")

        # 6. ASYNC MESSAGING & QUEUES
        with Cluster("Async Messaging & Orchestration"):
            pubsub = Pubsub("Cloud Pub/Sub\n(topic: 'ucp-order-events')")
            tasks = Tasks("Cloud Tasks\n(queue: 'pos-kitchen-sync')")

        # 7. PHYSICAL RETAIL & FULFILLMENT
        with Cluster("Physical Retail Execution (Milano Centrale Hub)"):
            dashboard = Tablet("Angular BOPIS Hub\n(:4201 Kitchen & Courier)")
            pos_kds = Server("Store POS & Kitchen KDS\n(Cash Registers & Screens)")
            smart_lockers = Server("IoT Smart Locker Fleet\n(PIN & Box Allocator)")

        # 8. EXTERNAL ENTERPRISE SYSTEMS
        with Cluster("Merchant Enterprise Systems"):
            core_ecom = Server("Core E-Commerce Platform\n(Shopify / ERP / Headless)")
            payment_psp = Server("Merchant Payment Provider\n(Stripe / Adyen / Bank PSP)")

        # INGRESS CONNECTIONS
        shopper_agent >> Edge(label="RFC 9421 REST / A2A") >> dns
        web_shopper >> Edge(label="Web MCP Tools") >> dns
        agentic_network >> Edge(label="UCP REST") >> dns

        dns >> armor >> api_gw >> Edge(label="Authenticated Ingress") >> ucp_core

        # INTERNAL COMPUTE FLOWS
        ucp_core >> Edge(color="#7b1fa2", style="dashed", label="Validate Rules") >> bopis_engine
        ucp_core >> Edge(color="#c2185b", label="Validate Mandate") >> ap2_verifier

        # INTELLIGENCE
        ucp_core <>> Edge(color="#f57c00", label="Semantic Negotiation\n& Combos") <>> gemini

        # PERSISTENCE & KEYS
        ucp_core <>> Edge(label="Read/Write Session & Cache") <>> firestore
        ap2_verifier >> Edge(label="Verify Keys") >> kms
        ap2_verifier >> Edge(color="#d32f2f", label="Execute Settlement") >> payment_psp
        ucp_core <>> Edge(label="Sync Stock & Catalog") <>> core_ecom

        # ASYNC FAN-OUT
        ucp_core >> Edge(color="#388e3c", label="Publish Confirmed Order") >> pubsub
        pubsub >> Edge(label="Event Push") >> ws_gw >> Edge(label="Sub-second WebSocket") >> dashboard
        pubsub >> Edge(label="Enqueue") >> tasks
        tasks >> Edge(label="Reliable HTTP Push") >> pos_kds
        tasks >> Edge(label="PIN Webhook") >> smart_lockers

    print(f"✅ Architecture diagram successfully generated at: {output_path}.png and {output_path}.svg")


if __name__ == "__main__":
    generate_architecture_diagram()
