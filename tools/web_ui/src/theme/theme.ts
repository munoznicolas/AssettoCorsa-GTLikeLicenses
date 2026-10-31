import { createTheme, ThemeOptions } from "@mui/material/styles";

export const getDesignTokens = (mode: "light" | "dark"): ThemeOptions => ({
  palette: {
    mode,
    ...(mode === "dark"
      ? {
          background: {
            default: "#141415",
            paper: "#19191b",
          },
          text: {
            primary: "#ededed",
            secondary: "#a1a1a6",
          },
          divider: "rgba(255, 255, 255, 0.08)",
          primary: {
            main: "#e11d48", // Motorsport red
            contrastText: "#ffffff",
          },
          secondary: {
            main: "#232325",
            contrastText: "#ededed",
          },
          success: {
            main: "#4cc38a",
            contrastText: "#ffffff",
          },
          error: {
            main: "#e5484d",
            contrastText: "#ffffff",
          },
          warning: {
            main: "#f59e0b",
            contrastText: "#000000",
          },
          info: {
            main: "#38bdf8",
            contrastText: "#000000",
          },
        }
      : {
          background: {
            default: "#fafafa",
            paper: "#ffffff",
          },
          text: {
            primary: "#171717",
            secondary: "#525252",
          },
          divider: "rgba(0, 0, 0, 0.08)",
          primary: {
            main: "#e11d48",
            contrastText: "#ffffff",
          },
          secondary: {
            main: "#f4f4f5",
            contrastText: "#171717",
          },
          success: {
            main: "#16a34a",
            contrastText: "#ffffff",
          },
          error: {
            main: "#dc2626",
            contrastText: "#ffffff",
          },
          warning: {
            main: "#b45309",
            contrastText: "#ffffff",
          },
          info: {
            main: "#0284c7",
            contrastText: "#ffffff",
          },
        }),
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: { fontWeight: 600 },
    h2: { fontWeight: 600 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    button: {
      textTransform: "none",
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 6,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          boxShadow: "none",
          "&:hover": {
            boxShadow: "none",
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({
          backgroundColor: theme.palette.mode === "dark" ? "#232325" : "#f4f4f5",
          fontSize: "13px",
          "& .MuiOutlinedInput-notchedOutline": {
            borderColor: theme.palette.divider,
          },
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: theme.palette.mode === "dark" ? "rgba(255, 255, 255, 0.2)" : "rgba(0, 0, 0, 0.2)",
          },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: theme.palette.mode === "dark" ? "#52525b" : "#18181b",
            borderWidth: "1px",
          },
        }),
        input: {
          padding: "7px 12px",
        },
      },
    },
    MuiAutocomplete: {
      styleOverrides: {
        root: {
          "& .MuiInputLabel-root": {
            fontSize: "12px",
            transform: "translate(12px, 8px) scale(1)",
            "&.MuiInputLabel-shrink": {
              transform: "translate(12px, -7px) scale(0.75)",
            },
          },
        },
        paper: ({ theme }) => ({
          backgroundColor: theme.palette.mode === "dark" ? "#19191b" : "#ffffff",
          border: `1px solid ${theme.palette.divider}`,
          boxShadow: theme.palette.mode === "dark" ? "0 8px 24px rgba(0, 0, 0, 0.5)" : "0 8px 24px rgba(0, 0, 0, 0.08)",
          borderRadius: 8,
          marginTop: 4,
        }),
        listbox: {
          fontSize: "12.5px",
          padding: 4,
          "& .MuiAutocomplete-option": {
            borderRadius: 4,
            padding: "6px 10px",
            minHeight: "auto",
            '&[aria-selected="true"]': {
              backgroundColor: "rgba(225, 29, 72, 0.12)",
              color: "#e11d48",
            },
          },
        },
      },
    },
  },
});

export const createAppTheme = (mode: "light" | "dark") => createTheme(getDesignTokens(mode));
