import { createTheme } from "@mui/material/styles";
export const theme = createTheme({
  palette: {
    primary: { main: "#2864a9" },
    background: { default: "#f5f7fa", paper: "#ffffff" },
    text: { primary: "#203047", secondary: "#617087" },
  },
  typography: {
    fontFamily: '"Segoe UI", system-ui, sans-serif',
    fontSize: 13,
    button: { textTransform: "none", fontWeight: 600 },
  },
  shape: { borderRadius: 7 },
  components: {
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiTextField: { defaultProps: { size: "small", fullWidth: true } },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 600, background: "#f7f9fc", whiteSpace: "nowrap" },
        root: { borderColor: "#e8edf3", fontSize: 12 },
      },
    },
  },
});
