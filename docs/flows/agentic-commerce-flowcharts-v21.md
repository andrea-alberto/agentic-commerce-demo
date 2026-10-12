# Technical Flowcharts (High-Legibility Slide Edition v21): Agent Client vs. Agent Server

This document presents high-resolution, presentation-optimized **Mermaid Flowcharts (flowchart LR)** mapping the execution logic, decision trees, and cryptographic steps of **ACP** and **UCP + AP2**.

To maximize legibility within slide decks, these flowcharts:
1. **Use Left-to-Right layout (`flowchart LR`)** instead of Top-Down (`graph TD`) to naturally fit 16:9 presentation slides.
2. **Increase spacing and use smooth curves** using Mermaid config (`nodeSpacing: 75`, `rankSpacing: 140`, `curve: 'basis'`).
3. **Declare logical nodes inside explicit Subgraphs on EVERY scenario** to physically cluster them into **Local [On-Device / Client-Side]** and **Cloud [In-Cloud / Server-Side]** environments. This mathematically guarantees that client-side components like `Stripe Client` or `Wallet` stay grouped on the left, preventing Mermaid's layout engine from pulling them to the right and ensuring absolute visual consistency across the entire slide deck.
4. **Avoid parentheses in connection labels** (e.g. replacing `- Discovery` instead of `(Discovery)`) as Mermaid's parser interprets parentheses as shape borders and throws syntax errors.
5. **Group self-loops and consecutive steps** into a single arc using HTML `<br/>` line breaks (bypassing the mermaid.live multiple self-loop rendering bug).
6. **Separate Client-side vs. Server-side counterparts symmetrically**:
    * **Stripe Client (Elements SDK)** vs. **Stripe Server (PSP API)** in ACP.
    * **Credentials Provider (Wallet)** vs. **Payment Issuer (Bank Server)** in AP2.
    * **Merchant ECP Frame** vs. **Merchant ECP Server** in UCP Embedded.
7. **Integrate UCP Discovery explicitly** (`GET /.well-known/ucp` and `GET /.well-known/agent-card.json` for A2A) in all relevant UCP/AP2 scenarios to ensure absolute technical rigor and slide independence.
8. **Ensure actor consistency**: The user's cloud-hosted orchestrator is uniformly named `Agent Server LLM` across all scenarios.

---

## SCENARIO 1: Human-Present (Real-Time Conversational Purchase)

### 1.1 ACP Flow (Stripe / OpenAI)
This flowchart shows how Stripe's secure Elements are embedded on the Client device, bypassing the Server entirely for raw payment entry to maintain strict PCI compliance.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef psp fill:#EBDEF0,stroke:#8E44AD,color:#4A235A;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
        StripeClient[Stripe Client<br/>Elements SDK]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant<br/>Endpoint]
        StripeServer[Stripe API<br/>PSP Server]
        spacer12[ ]
    end

    User -->|1. 'Buy Product X'| Client
    Client -->|2. Forward request| Server
    Server -->|3. POST create<br/>checkout| Merchant
    Merchant -->|4. Return Session ID<br/>& totals| Server
    Server -->|5. Deliver structured<br/>UI schema| Client
    Client -->|6. Render<br/>checkout screen| User
    User -->|7. Select options<br/>& tap Pay| Client
    Client -->|8. Send updated<br/>selections| Server
    Server -->|9. POST update<br/>checkout| Merchant
    User -->|10. Input card<br/>info safely| StripeClient
    StripeClient -->|11. Transmit secure<br/>card data| StripeServer
    StripeServer --> spacer12
    spacer12 -->|12. Tokenize<br/>& return SPT| StripeClient
    StripeClient -->|13. Deliver SPT<br/>to Client| Client
    Client -->|14. Forward SPT -<br/>out of PCI<br/>scope| Server
    Server -->|15. POST complete<br/>checkout + SPT| Merchant
    Merchant -->|16. Charge funds<br/>with SPT| StripeServer
    StripeServer -->|17. Capture success<br/>confirmation| Merchant
    Merchant -->|18. Confirm<br/>order success| Server
    Server -->|19. Deliver<br/>receipt data| Client
    Client -->|20. Show order summary| User

    class User buyer;
    class Client client;
    class Server server;
    class StripeClient psp;
    class StripeServer psp;
    class Merchant merchant;

    style spacer12 fill:none,stroke:none,color:none,width:0px,height:0px;
    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

---

### 1.2 UCP + AP2 Flow (Google / Shopify)
This flowchart illustrates the use of on-device biometric validation to authorize the cryptographically secure **Cart Mandate** and **Payment Mandate** credentials.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef wallet fill:#FADBD8,stroke:#C0392B,color:#641E16;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef issuer fill:#EAECEE,stroke:#7F8C8D,color:#2C3E50;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
        Wallet[Credentials<br/>Provider Wallet]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant<br/>Endpoint]
        Issuer[Payment Network<br/>Bank Server]
    end

    User -->|1. 'Buy Product Y'| Client
    Client -->|2. Delegate task| Server
    Server -->|3. GET ucp<br/>- Discovery| Merchant
    Merchant -->|4. Return UCP profile<br/>& capabilities| Server
    Server -->|5. POST Universal<br/>Cart API| Merchant
    Merchant -->|6. Return cart items<br/>& taxes| Server
    Server -->|7. Forward payment<br/>challenge| Client
    Client -->|8. Render checkout UI| User
    User -->|9. TouchID/FaceID<br/>approval| Wallet
    Wallet -->|10a. Sign Cart<br/>Mandate VC<br/>10b. Sign Payment<br/>Mandate VC| Wallet
    Wallet -->|11. Pass signed<br/>Mandate VCs| Client
    Client -->|12. Send Mandates<br/>to Server| Server
    Server -->|13. Submit Mandates<br/>to complete| Merchant
    Merchant -->|14. Settle with<br/>Payment Mandate| Issuer
    Issuer -->|15. Verify VC<br/>signatures &<br/>authorize charge| Issuer
    Issuer -.->|16. Return<br/>Payment-Receipt| Merchant
    Merchant -->|17. Confirm<br/>order success| Server
    Server -->|18. Deliver<br/>final receipt| Client
    Client -->|19. Display<br/>Purchase Complete| User

    class User buyer;
    class Client client;
    class Wallet wallet;
    class Server server;
    class Merchant merchant;
    class Issuer issuer;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

---

---

### 1.3 UCP Standard Flow (Google Pay / Shop Pay - Without AP2)
This flowchart shows a native UCP checkout using a traditional Payment Handler (e.g. Google Pay or Shop Pay) when the AP2 Mandates extension is not negotiated.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef wallet fill:#FADBD8,stroke:#C0392B,color:#641E16;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef psp fill:#EBDEF0,stroke:#8E44AD,color:#4A235A;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
        Wallet[Credentials<br/>Provider Wallet]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant<br/>Endpoint]
        PSP[Merchant PSP<br/>Gateway]
    end

    User -->|1. 'Buy Product Y'| Client
    Client -->|2. Delegate task| Server
    Server -->|3. GET ucp<br/>- Discovery| Merchant
    Merchant -->|4. Return profile<br/>& Payment Handlers| Server
    Server -->|5. POST /checkouts| Merchant
    Merchant -->|6. Return checkout<br/>& Handlers| Server
    Server -->|7. Forward checkout<br/>& Handlers| Client
    Client -->|8. Render UI &<br/>Payment Button| User
    User -->|9. Tap Pay &<br/>TouchID/FaceID| Wallet
    Wallet -->|10. Issue tokenized<br/>Payment Credential| Client
    Client -->|11. Send Payment<br/>Credential| Server
    Server -->|12. POST complete<br/>checkout + Token| Merchant
    Merchant -->|13. Charge token<br/>via PSP| PSP
    PSP -->|14. Confirm charge<br/>success| Merchant
    Merchant -->|15. Confirm<br/>order success| Server
    Server -->|16. Deliver final<br/>receipt| Client
    Client -->|17. Display<br/>Purchase Complete| User

    class User buyer;
    class Client client;
    class Wallet wallet;
    class Server server;
    class Merchant merchant;
    class PSP psp;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

## SCENARIO 2: Human-Not-Present (Asynchronous / Delegated Purchase)

### 2.1 ACP Flow (Stripe / OpenAI)
This flowchart details how the backend Agent Server triggers an asynchronous purchase without client-side user intervention, utilizing pre-authorized consent registered in Stripe's vaults.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef psp fill:#EBDEF0,stroke:#8E44AD,color:#4A235A;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
        StripeClient[Stripe Client<br/>Elements SDK]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant<br/>Endpoint]
        StripeServer[Stripe API<br/>PSP Server]
        PriceCheck{Price < $100?}
    end

    User -->|1. 'Buy X if<br/>under $100'| Client
    Client -->|2. Register background<br/>task| Server
    User -->|3. Setup deferred<br/>debit vault consent| StripeClient
    StripeClient -->|4. Store authorized<br/>consent limit| StripeServer
    Server -->|5. Query pricing<br/>periodically| Server
    Server --> PriceCheck
    PriceCheck -->|No, continue| Server
    PriceCheck -->|Yes: $95| Merchant
    Merchant -->|6. POST create<br/>checkout| Server
    Server -->|7. Request SPT for $95<br/>using vaulted consent| StripeServer
    StripeServer -->|8. Verify consent<br/>limits & issue<br/>scoped SPT| Server
    Server -->|9. POST complete<br/>checkout + SPT| Merchant
    Merchant -->|10. Settle funds<br/>with SPT| StripeServer
    StripeServer -->|11. Capture OK| Merchant
    Merchant -->|12. Return order<br/>receipt| Server
    Server -->|13. Push notification<br/>payload| Client
    Client -->|14. Display push<br/>notification| User

    class User buyer;
    class Client client;
    class Server server;
    class StripeClient psp;
    class StripeServer psp;
    class Merchant merchant;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

---

### 2.2 UCP + AP2 Flow (Google / Shopify)
This flowchart demonstrates how the local Agent Client background daemon validates the transaction against the **Intent Mandate** and signs the transaction credentials on-device, completely headless.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef wallet fill:#FADBD8,stroke:#C0392B,color:#641E16;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef issuer fill:#EAECEE,stroke:#7F8C8D,color:#2C3E50;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Wallet[Credentials<br/>Provider Wallet]
        Client[Agent Client<br/>Daemon]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant Endpoint<br/>UCP]
        Issuer[Payment Network<br/>Bank Server]
        ConditionCheck{Match found es. $90?}
    end

    User -->|1. Setup limits<br/>Max $100| Wallet
    Wallet -->|2. Issue Intent<br/>Mandate VC| Client
    Client -->|3. Register task<br/>+ Intent VC| Server
    Server -->|4. GET ucp<br/>- Discovery| Merchant
    Merchant -->|5. Return UCP profile<br/>& capabilities| Server
    Server -->|6. Monitor price<br/>& stock| Server
    Server --> ConditionCheck
    ConditionCheck -->|No| Server
    ConditionCheck -->|Yes| Merchant
    Merchant -->|7. Return checkout<br/>challenge| Server
    Server -->|8. Request background<br/>signing| Client
    Client <-->|9. Query validation<br/>Wallet verifies<br/>limits & signs<br/>Mandate VCs| Wallet
    Client -->|10. Send Mandates<br/>to Server| Server
    Server -->|11. Submit Mandates<br/>to complete| Merchant
    Merchant -->|12. Process with<br/>chained Mandates| Issuer
    Issuer -->|13. Verify<br/>cryptographic<br/>chain & authorize| Issuer
    Issuer -.->|14. Return<br/>Payment-Receipt| Merchant
    Merchant -->|15. Confirm order| Server
    Server -->|16. Push success<br/>confirmation| Client
    Client -->|17. Show Purchase<br/>Done alert| User

    class User buyer;
    class Wallet wallet;
    class Client client;
    class Server server;
    class Merchant merchant;
    class Issuer issuer;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

---

## SCENARIO 3: Personalized Offer Negotiation

### 3.1 ACP Flow (Stripe / OpenAI)
This flowchart shows how negotiations on discounts occur programmatically at the Agent Server level based on discount extensions.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant<br/>Backend]
    end

    User -->|1. 'Ask for bundle<br/>discount on X+Y'| Client
    Client -->|2. Send intent| Server
    Server -->|3. POST negotiations<br/>Capability| Merchant
    Merchant -->|4. Activate Discount<br/>Extension<br/>5. Verify loyalty<br/>& inventory| Merchant
    Merchant -->|6. Return coupon<br/>proposal -15%| Server
    Server -->|7. Send discount text| Client
    Client -->|8. Present offer<br/>to User| User
    User -->|9. Accept proposal| Client
    Client -->|10. Forward acceptance| Server
    Server -->|11. POST checkout<br/>with coupon| Merchant
    Merchant -->|12. Return discounted<br/>checkout session| Server
    Server -.->|13. Hand-off:<br/>Proceed to pay -<br/>Scenario 1.1| Merchant

    class User buyer;
    class Client client;
    class Server server;
    class Merchant merchant;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

---

### 3.2 UCP + A2A Flow (Google / Shopify)
This flowchart maps out how the Buyer's Agent Server establishes an **Agent2Agent (A2A)** connection to negotiate deals with the Merchant's internal, autonomous **NAT Agents**.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef nat fill:#EAECEE,stroke:#7F8C8D,color:#2C3E50;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        MerchantEndpoint[Merchant A2A<br/>Endpoint]
        NAT[Merchant NAT<br/>Agents]
    end

    User -->|1. 'Plan trip &<br/>negotiate bundle'| Client
    Client -->|2. Pass context & goal| Server
    Server -->|3. GET .well-known/ucp<br/>- Discovery<br/>GET agent-card.json<br/>- A2A Skills| MerchantEndpoint
    MerchantEndpoint -->|4. Return UCP profile<br/>& signed Agent Card| Server
    Server -->|5. Open secure A2A<br/>connection &<br/>share context| MerchantEndpoint
    MerchantEndpoint -->|6. Route inquiry| NAT
    NAT -->|7a. Pricing Agent<br/>computes margin<br/>7b. Promotion Agent<br/>creates proposal<br/>7c. Sign Offer VC| NAT
    NAT -->|8. Deliver<br/>Signed Offer| MerchantEndpoint
    MerchantEndpoint -->|9. Return structured<br/>A2A response| Server
    Server -->|10. Translate offer<br/>to chat| Client
    Client -->|11. Show proposal<br/>details in chat| User
    User -->|12. Tap Accept<br/>Bundle| Client
    Client -->|13. Initiate AP2<br/>Payment| Server
    Server -.->|14. Hand-off:<br/>Proceed to AP2<br/>secured checkout| MerchantEndpoint

    class User buyer;
    class Client client;
    class Server server;
    class MerchantEndpoint merchant;
    class NAT nat;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

---

## SCENARIO 4: UCP Checkout Variations

### 4.1 UCP Native Checkout API
In Native Checkout, the Agent Client manages the complete form validation and layout rendering on-device, processing a raw JSON challenge received by the Agent Server from the Merchant's API.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef wallet fill:#FADBD8,stroke:#C0392B,color:#641E16;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef issuer fill:#EAECEE,stroke:#7F8C8D,color:#2C3E50;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
        Wallet[Credentials<br/>Provider Wallet]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant<br/>Backend]
        Issuer[Payment Network<br/>Bank Server]
    end

    User -->|1. 'Buy Y' - Init| Client
    Client -->|2. Delegate buy<br/>task| Server
    Server -->|3. GET ucp<br/>- Discovery| Merchant
    Merchant -->|4. Return UCP profile<br/>& capabilities| Server
    Server -->|5. POST /checkouts| Merchant
    Merchant -->|6. Return raw JSON<br/>checkout schema| Server
    Server -->|7. Forward schema| Client
    Client -->|8. Render native form| User
    User -->|9. Update shipping<br/>& options| Client
    Client -->|10. Forward form<br/>choices| Server
    Server -->|11. PUT /checkouts/id| Merchant
    Merchant -->|12. Return updated<br/>totals & challenge| Server
    Server -->|13. Forward payment<br/>challenge| Client
    Client -->|14. Request biometric<br/>payment auth| Wallet
    User -->|15. TouchID/FaceID<br/>approval| Wallet
    Wallet -->|16a. Sign Cart<br/>Mandate VC<br/>16b. Sign Payment<br/>Mandate VC| Wallet
    Wallet -->|17. Return Cart<br/>& Payment VCs| Client
    Client -->|18. Send Mandates<br/>to Server| Server
    Server -->|19. POST complete<br/>checkout| Merchant
    Merchant -->|20. Settle with<br/>Payment Mandate| Issuer
    Issuer -->|21. Verify<br/>cryptographic<br/>chain & authorize| Issuer
    Issuer -.->|22. Return<br/>Payment-Receipt| Merchant
    Merchant -->|23. Confirm<br/>order success| Server
    Server -->|24. Deliver receipt UI| Client
    Client -->|25. Show order summary| User

    class User buyer;
    class Client client;
    class Wallet wallet;
    class Server server;
    class Merchant merchant;
    class Issuer issuer;

    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```

---

### 4.2 UCP Embedded Checkout (ECP)
In ECP, the Agent Client hosts a cross-origin webview/iframe belonging directly to the Merchant. Safe token sharing is maintained on-device using HTML5 secure cross-origin postMessage APIs.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': {
    'nodeSpacing': 75,
    'rankSpacing': 140,
    'curve': 'basis'
  }
}}%%
flowchart LR
    %% Shared base styles (large bold text, distinct borders)
    classDef default font-size:22px,font-weight:bold,stroke-width:3px;

    %% Palette colors with dark contrasting text
    classDef buyer fill:#EBF5FB,stroke:#2980B9,color:#1B4F72;
    classDef client fill:#FCF3CF,stroke:#F39C12,color:#7E5109;
    classDef wallet fill:#FADBD8,stroke:#C0392B,color:#641E16;
    classDef server fill:#FDEDEC,stroke:#E74C3C,color:#78281F;
    classDef merchant fill:#D5F5E3,stroke:#27AE60,color:#145A32;
    classDef ecp fill:#EAECEE,stroke:#7F8C8D,color:#2C3E50;
    classDef issuer fill:#EAECEE,stroke:#7F8C8D,color:#2C3E50;

    subgraph Local [On-Device / Client-Side]
        User([Buyer /<br/>User])
        Client[Agent Client<br/>UI]
        Wallet[Credentials<br/>Provider Wallet]
        ECPFrame[Merchant ECP<br/>Frame]
    end

    subgraph Cloud [In-Cloud / Server-Side]
        Server[Agent Server<br/>LLM]
        Merchant[Merchant ECP<br/>Server]
        Issuer[Payment Network<br/>Bank Server]
        spacer20[ ]
    end

    User -->|1. 'Checkout Y' - Init| Client
    Client -->|2. Initiate checkout<br/>flow| Server
    Server -->|3. GET ucp<br/>- Discovery| Merchant
    Merchant -->|4. Return UCP profile<br/>& capabilities| Server
    Server -->|5. GET embedded<br/>session| Merchant
    Merchant -->|6. Return secure<br/>ECP URL & token| Server
    Server -->|7. Send session<br/>token & URL| Client
    Client -->|8. Mount secure<br/>webview / iframe| ECPFrame
    Client -->|9. window.postMessage:<br/>Share shipping details| ECPFrame
    ECPFrame -.->|10. Render<br/>checkout screen<br/>& calculate in-frame| User
    User -->|11. Confirm order<br/>& tap Pay| ECPFrame
    ECPFrame -->|12. Request AP2<br/>credentials| Wallet
    User -->|13. TouchID/FaceID<br/>approval| Wallet
    Wallet -->|14a. Sign Cart<br/>Mandate VC<br/>14b. Sign Payment<br/>Mandate VC| Wallet
    Wallet -->|15. Return Cart<br/>& Payment VCs| ECPFrame
    ECPFrame -->|16. POST complete<br/>checkout| Merchant
    Merchant -->|17. Settle with<br/>Payment Mandate| Issuer
    Issuer -->|18. Verify<br/>cryptographic<br/>chain & authorize| Issuer
    Issuer -.->|19. Return<br/>Payment-Receipt| Merchant
    Merchant -.-> spacer20
    spacer20 -.->|20. Settle &<br/>confirm success| ECPFrame
    ECPFrame -->|21. postMessage:<br/>Success confirm| Client
    Client -->|22. Register done<br/>& close webview| Server
    Server -->|23. Sync chat &<br/>delivery receipt| Client
    Client -->|24. Show final<br/>receipt to user| User

    class User buyer;
    class Client client;
    class Wallet wallet;
    class Server server;
    class ECPFrame ecp;
    class Merchant merchant;
    class Issuer issuer;

    style spacer20 fill:none,stroke:none,color:none,width:0px,height:0px;
    style Local fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
    style Cloud fill:none,stroke:#BDC3C7,stroke-width:2px,stroke-dasharray: 5 5;
```
