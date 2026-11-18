import { createTheme } from "@mui/material/styles";
export const theme = createTheme({
  palette: {
    primary: { main: "#52789e", dark: "#466b8f", light: "#eaf0f6" },
    success: { main: "#4b8065", light: "#edf6f1" },
    warning: { main: "#9a7b43", light: "#fbf5e9" },
    error: { main: "#a86168", light: "#fbeff0" },
    info: { main: "#52789e", light: "#edf2f8" },
    background: { default: "#f7f8fa", paper: "#ffffff" },
    divider: "#e2e6eb",
    text: { primary: "#344054", secondary: "#667085", disabled: "#98a2b3" },
  },
  typography: {
    fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
    fontSize: 13,
    h1: { fontSize: "25px", fontWeight: 600, lineHeight: 1.3, letterSpacing: "-0.45px" },
    h2: { fontSize: "17px", fontWeight: 600 },
    h3: { fontSize: "15px", fontWeight: 600 },
    body1: { fontSize: "14px", lineHeight: 1.55 },
    body2: { fontSize: "13px", lineHeight: 1.5 },
    button: { textTransform: "none", fontWeight: 600, fontSize: "13px" },
  },
  shape: { borderRadius: 7 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true, size: "medium" },
      styleOverrides: {
        root: {
          minHeight: 36,
          borderRadius: 7,
          boxShadow: "none",
          "&.MuiButton-containedPrimary": {
            backgroundColor: "#52789e",
            "&:hover": { backgroundColor: "#466b8f", boxShadow: "none" },
          },
        },
        outlined: { borderColor: "#d0d5dd", color: "#344054", "&:hover": { borderColor: "#98a2b3", backgroundColor: "#f3f5f7" } },
      },
    },
    MuiTextField: { defaultProps: { size: "small", fullWidth: true } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 7, backgroundColor: "#ffffff", "& .MuiOutlinedInput-notchedOutline": { borderColor: "#d0d5dd" }, "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: "#98a2b3" }, "&.Mui-focused .MuiOutlinedInput-notchedOutline": { borderColor: "#52789e", borderWidth: 1 } },
        input: { fontSize: 13, paddingTop: 10, paddingBottom: 10 },
      },
    },
    MuiInputLabel: { styleOverrides: { root: { fontSize: 13 } } },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 600, color: "#475467", background: "#f7f8fa", whiteSpace: "nowrap" },
        root: { borderColor: "#e9edf2", fontSize: 12, padding: "9px 12px" },
      },
    },
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
    MuiTabs: { styleOverrides: { indicator: { backgroundColor: "#52789e" } } },
    MuiTab: { styleOverrides: { root: { minHeight: 42, textTransform: "none", fontSize: 13, fontWeight: 500 } } },
    MuiDialog: { styleOverrides: { paper: { border: "1px solid #e2e6eb", borderRadius: 9, boxShadow: "0 12px 32px rgb(16 24 40 / 12%)" } } },
  },
});
