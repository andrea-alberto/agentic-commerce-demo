import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection, provideExperimentalWebMcpTools } from '@angular/core';
import { webMcpTools } from './webmcp.tools';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    // Official Angular 22 WebMCP tools registration (https://angular.dev/ai/webmcp)
    provideExperimentalWebMcpTools(webMcpTools as any),
  ]
};
