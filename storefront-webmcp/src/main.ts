import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

// WebMCP Browser Standard & Chrome AI Polyfills (WebMCP Inspector Compliance)
if (typeof window !== 'undefined') {
  const win = window as any;

  // 1. window.ai (Chrome Prompt API / Gemini Nano) Polyfill
  try {
    if (!win.ai) {
      win.ai = {
        languageModel: {
          capabilities: async () => ({
            available: 'readily',
            defaultTemperature: 0.7,
            defaultTopK: 40,
            maxTopK: 128
          }),
          create: async () => ({
            prompt: async (text: string) => `[Gemini Nano Client]: Elaborata richiesta: ${text}`,
            promptStreaming: (text: string) => {
              return new ReadableStream({
                start(controller) {
                  controller.enqueue(`[Gemini Nano]: ${text}`);
                  controller.close();
                }
              });
            },
            countPromptTokens: async () => 24,
            destroy: () => {}
          })
        }
      };
    }
  } catch (e) {
    console.debug('window.ai polyfill skipped:', e);
  }

  // 2. WebMCP Standard Polyfill (Safe registration without overwriting read-only getters)
  try {
    const existingMC = win.document?.modelContext || win.navigator?.modelContext;
    if (!win.navigator.modelContext) {
      if (existingMC) {
        win.navigator.modelContext = existingMC;
      } else {
        const registry = new Map<string, any>();
        const mc = {
          registerTool: async (tool: any) => {
            registry.set(tool.name, tool);
            console.log(`%c[Angular 22 WebMCP] Registered tool: ${tool.name}`, 'color: #00d2ff; font-weight: bold;', tool);
          },
          unregisterTool: async (name: string) => {
            registry.delete(name);
            console.log(`[Angular 22 WebMCP] Unregistered tool: ${name}`);
          },
          getTools: () => Array.from(registry.values()),
          listTools: async () => Array.from(registry.values()),
          callTool: async (name: string, args: any) => {
            const tool = registry.get(name);
            if (!tool) throw new Error(`Tool '${name}' non trovato nel registry WebMCP.`);
            return await tool.execute(args);
          }
        };
        win.navigator.modelContext = mc;
        win.modelContext = mc;
      }
    }
  } catch (e) {
    console.debug('WebMCP polyfill skipped:', e);
  }
}

bootstrapApplication(App, appConfig)
  .catch((err) => console.error('Bootstrap error:', err));
