import { createContext, useContext } from "react";
import { useAuth } from "./useAuth";

const PreferencesContext = createContext(null);

const DEFAULT_PREFERENCES = {
  distance_unit: "km",
  temperature_unit: "c",
  time_format: "24h",
};

export function PreferencesProvider({ children }) {
  const auth = useAuth();

  const preferences = {
    distance_unit: auth.user?.distance_unit || DEFAULT_PREFERENCES.distance_unit,
    temperature_unit: auth.user?.temperature_unit || DEFAULT_PREFERENCES.temperature_unit,
    time_format: auth.user?.time_format || DEFAULT_PREFERENCES.time_format,
  };

  return (
    <PreferencesContext.Provider value={{ preferences }}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error("usePreferences must be used within a PreferencesProvider");
  }
  return context;
}
