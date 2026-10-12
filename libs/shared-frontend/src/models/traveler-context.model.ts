// Copyright 2026 UCP Authors / GDG DevFest Milano 2026

export interface TrainTicket {
  train_number: string;
  pnr: string;
  origin: string;
  destination: string;
  departure_time: string; // HH:MM
  platform: string;
  carriage: string;
  seat: string;
  class_service: string;
}

export interface TravelerPreferences {
  dietary: string;
  preferred_fulfillment: 'in_seat_train' | 'pickup_locker' | 'pickup_express' | 'table_service';
  max_budget_cents: number;
  notes: string;
  allergens_to_avoid?: string[];
  health_goals?: string[];
  avoid_ultra_processed?: boolean;
  coffee_preference?: string;
}

export interface AP2Delegation {
  enabled: boolean;
  mandate_type: string;
  max_amount_cents: number;
  currency: string;
  credential_manager: string;
  token_id: string;
}

export interface TravelerContext {
  traveler_id: string;
  name: string;
  email: string;
  loyalty_tier: string;
  loyalty_code: string;
  scenario_preset_id: string;
  ticket: TrainTicket;
  preferences: TravelerPreferences;
  ap2: AP2Delegation;
}

export interface ScenarioPreset {
  id: string;
  title: string;
  short_label: string;
  badge: string;
  description: string;
  context: Partial<TravelerContext>;
}

export const DEFAULT_SCENARIO_PRESETS: ScenarioPreset[] = [
  {
    id: 'scenario_departing_soon',
    title: 'Scenario A: Fretta • In Partenza tra 15 min',
    short_label: '15 min • Binario 14',
    badge: '🚆 Consegna a Bordo',
    description: 'Il Frecciarossa 9540 parte a breve dal binario 14. L\'agente negozia la consegna diretta alla carrozza 4 posto 12D.',
    context: {
      scenario_preset_id: 'scenario_departing_soon',
      ticket: {
        train_number: 'Frecciarossa 9540',
        pnr: 'FR-9540-MR',
        origin: 'Milano Centrale',
        destination: 'Roma Termini',
        departure_time: '13:10',
        platform: '14',
        carriage: '4',
        seat: '12D',
        class_service: 'Area Silenzio • Prima Classe'
      },
      preferences: {
        dietary: 'No carne rossa • Piatti freschi e leggeri',
        preferred_fulfillment: 'in_seat_train',
        max_budget_cents: 2500,
        notes: 'Consegna tassativa a bordo prima della chiusura porte'
      }
    }
  },
  {
    id: 'scenario_transit_locker',
    title: 'Scenario B: Coincidenza 45 min • Sosta Stazione',
    short_label: '45 min • Smart Locker',
    badge: '🥪 Locker Interrato',
    description: 'Il viaggiatore ha 45 minuti di sosta. L\'agente sceglie lo Smart Locker contactless (€0 spese consegna).',
    context: {
      scenario_preset_id: 'scenario_transit_locker',
      ticket: {
        train_number: 'Italo 9923',
        pnr: 'IT-9923-TR',
        origin: 'Milano Centrale',
        destination: 'Napoli Centrale',
        departure_time: '13:55',
        platform: '18',
        carriage: '6',
        seat: '21B',
        class_service: 'Club Executive'
      },
      preferences: {
        dietary: 'Opzione vegetariana o vegana',
        preferred_fulfillment: 'pickup_locker',
        max_budget_cents: 2000,
        notes: 'Ritiro contactless allo Smart Locker del piano interrato'
      }
    }
  },
  {
    id: 'scenario_fitness_specialty',
    title: 'Scenario C: Fitness, Basso Sale & Cold Brew Specialty',
    short_label: 'Fitness • Smart Locker',
    badge: '⚡ Low-Salt & Specialty',
    description: 'Viaggiatore attento alla salute: cibi poco processati (NOVA 1-3), basso sale, alto apporto proteico e Cold Brew Specialty idoneo per Smart Locker.',
    context: {
      scenario_preset_id: 'scenario_fitness_specialty',
      ticket: {
        train_number: 'Frecciarossa 9540',
        pnr: 'FR-9540-MR',
        origin: 'Milano Centrale',
        destination: 'Roma Termini',
        departure_time: '13:10',
        platform: '14',
        carriage: '4',
        seat: '12D',
        class_service: 'Area Silenzio • Prima Classe'
      },
      preferences: {
        dietary: 'High-protein • Basso sale • Senza glutine/lattosio',
        preferred_fulfillment: 'pickup_locker',
        max_budget_cents: 3000,
        allergens_to_avoid: ['Glutine', 'Lattosio'],
        health_goals: ['high_protein', 'low_salt'],
        avoid_ultra_processed: true,
        coffee_preference: 'cold_brew_specialty',
        notes: 'Cold Brew estrazione a freddo 16h + snack non ultraprocessati allo smart locker'
      }
    }
  }
];
