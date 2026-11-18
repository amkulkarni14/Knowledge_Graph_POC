import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GlobalStyles, ThemeProvider } from "@mui/material";
import { StyledEngineProvider } from "@mui/material/styles";
import { theme } from "../styles/theme";
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5000, retry: false, refetchOnWindowFocus: false },
    mutations: { retry: false, gcTime: 0 },
  },
});
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <StyledEngineProvider enableCssLayer>
        <GlobalStyles styles="@layer theme, base, mui, components, utilities;" />
        <ThemeProvider theme={theme}>{children}</ThemeProvider>
      </StyledEngineProvider>
    </QueryClientProvider>
  );
}
