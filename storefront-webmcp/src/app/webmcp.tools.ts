// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
// Conformance to Angular 22 WebMCP Standard (https://angular.dev/ai/webmcp)

let activeMcpService: any = null;

export function setActiveMcpService(service: any) {
  activeMcpService = service;
}

export function getActiveMcpService(): any {
  return activeMcpService;
}

export const webMcpTools = [
  {
    name: 'searchCatalog',
    description: (
      'Cerca alimenti caldi/freddi, bevande ed accessori nel catalogo di Milano Centrale, ' +
      'aggiornando in tempo reale la barra di ricerca o i filtri di categoria visibili nella pagina web. ' +
      'Filtri di categoria disponibili nella UI: all, sandwiches, vegan, coffee, drinks, cold, hot, tech, gluten_free, lactose_free, high_protein, specialty. ' +
      'IMPORTANTE PER ACQUISTI MULTIPLI: Cerca un solo articolo alla volta. ' +
      'Se l\'utente richiede 2 o più prodotti non correlati (es. "una spremuta" e "un panino vegano"), ' +
      'non unire i termini in una sola ricerca: esegui prima la ricerca per il primo prodotto (es. "spremuta"), ' +
      'chiamando SUBITO "addToCart" con l\'ID individuato; solo DOPO esegui la seconda ricerca per il secondo prodotto (es. "panino vegano") ' +
      'ed aggiungilo con "addToCart". Esempi query: "panini", "panino vegano", "spremuta", "caffe", "croissant".'
    ),
    annotations: { readOnlyHint: true },
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Termine o nome dell\'articolo da cercare (es: panino vegano, spremuta, caffe, croissant). NON includere parole di comando come "aggiungi al carrello".' },
        category: { type: 'string', enum: ['all', 'sandwiches', 'vegan', 'coffee', 'drinks', 'cold', 'hot', 'tech', 'gluten_free', 'lactose_free', 'high_protein', 'specialty'], description: 'Categoria opzionale selezionata tra i filtri della UI' }
      }
    },
    execute: async (args: any) => {
      if (activeMcpService) {
        return await activeMcpService.executeWebMcpTool('searchCatalog', args);
      }
      return { error: 'McpService not initialized' };
    }
  },
  {
    name: 'selectCategory',
    description: (
      'Filtra i prodotti a video cliccando su uno dei chip di categoria della pagina web. ' +
      'Categorie disponibili: "sandwiches" (Panini & Toast), "vegan" (Vegano), "coffee" (Caffetteria), ' +
      '"drinks" (Bevande Fresche), "specialty" (Specialty Coffee), "gluten_free" (Senza Glutine AIC), ' +
      '"lactose_free" (Senza Lattosio), "high_protein" (High-Protein), "cold" (Freddi & Locker), ' +
      '"hot" (Caldi), "tech" (Accessori Tech), "all" (Mostra tutti).'
    ),
    annotations: { readOnlyHint: true },
    inputSchema: {
      type: 'object',
      properties: {
        category: {
          type: 'string',
          enum: ['all', 'sandwiches', 'vegan', 'coffee', 'drinks', 'specialty', 'gluten_free', 'lactose_free', 'high_protein', 'cold', 'hot', 'tech'],
          description: 'Identificativo del filtro di categoria da cliccare nella UI'
        }
      },
      required: ['category']
    },
    execute: async (args: any) => {
      if (activeMcpService) {
        return await activeMcpService.executeWebMcpTool('selectCategory', args);
      }
      return { error: 'McpService not initialized' };
    }
  },
  {
    name: 'getProductDetails',
    description: 'Ottieni scheda tecnica completa, allergeni, prezzo e valori nutrizionali di un prodotto tramite product_id.',
    annotations: { readOnlyHint: true },
    inputSchema: {
      type: 'object',
      properties: {
        product_id: { type: 'string', description: 'ID univoco del prodotto (es: BEV-007, VEG-012, PANIN-004)' }
      },
      required: ['product_id']
    },
    execute: async (args: any) => {
      if (activeMcpService) {
        return await activeMcpService.executeWebMcpTool('getProductDetails', args);
      }
      return { error: 'McpService not initialized' };
    }
  },
  {
    name: 'addToCart',
    description: (
      'Aggiunge un articolo al carrello della pagina web e aggiorna in tempo reale il badge e il totale a video. ' +
      'Accetta l\'ID del prodotto (es: "VEG-012", "BEV-007", "PAST-002") oppure direttamente il nome o termine dell\'articolo (es: "panino vegano", "spremuta d\'arancia").'
    ),
    annotations: { consequentialHint: true },
    inputSchema: {
      type: 'object',
      properties: {
        product_id: { type: 'string', description: 'ID univoco del prodotto (es: VEG-012, BEV-007) oppure nome dell\'articolo da aggiungere (es: panino vegano, spremuta)' },
        quantity: { type: 'integer', description: 'Quantità desiderata (default 1)' }
      },
      required: ['product_id']
    },
    execute: async (args: any) => {
      if (activeMcpService) {
        return await activeMcpService.executeWebMcpTool('addToCart', args);
      }
      return { error: 'McpService not initialized' };
    }
  },
  {
    name: 'configureFulfillment',
    description: (
      'Configura la modalità di ritiro (pickup_locker per Smart Locker piano interrato, oppure pickup_express per ritiro al banco) ' +
      'evidenziando e selezionando l\'opzione nella pagina web.'
    ),
    annotations: { consequentialHint: true },
    inputSchema: {
      type: 'object',
      properties: {
        method: { type: 'string', enum: ['pickup_locker', 'pickup_express', 'in_seat_train', 'table_service'], description: 'Metodo BOPIS di stazione (es. pickup_locker, pickup_express)' },
        details: { type: 'object', description: 'Dettagli facoltativi (slot_time, pin_code, train_number, carriage, seat, table_number)' }
      },
      required: ['method']
    },
    execute: async (args: any) => {
      if (activeMcpService) {
        return await activeMcpService.executeWebMcpTool('configureFulfillment', args);
      }
      return { error: 'McpService not initialized' };
    }
  },
  {
    name: 'prepareCheckout',
    description: 'Apre il cassetto di checkout a video con il riepilogo articoli e fulfillment per permettere all utente umano presente di verificare e autorizzare il pagamento finale (Human-Present).',
    annotations: { consequentialHint: true },
    inputSchema: {
      type: 'object',
      properties: {
        buyer_name: { type: 'string', description: 'Nome del viaggiatore (opzionale)' },
        buyer_email: { type: 'string', description: 'Email per codice di ritiro e QR (opzionale)' }
      }
    },
    execute: async (args: any) => {
      if (activeMcpService) {
        return await activeMcpService.executeWebMcpTool('prepareCheckout', args);
      }
      return { error: 'McpService not initialized' };
    }
  }
];
