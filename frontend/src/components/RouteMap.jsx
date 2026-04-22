import { useEffect } from "react";
import { CircleMarker, MapContainer, Marker, Popup, Polyline, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import { usePreferences } from "../hooks/usePreferences";
import { formatDateTime, formatDistanceKm } from "../utils/formatters";

const selectedIcon = new L.DivIcon({
  className: "selected-point-icon",
  html: "<span></span>",
  iconSize: [18, 18],
});

function FitToRoute({ coordinates }) {
  const map = useMap();

  useEffect(() => {
    if (!coordinates.length) {
      return;
    }
    map.fitBounds(coordinates, { padding: [24, 24] });
  }, [coordinates, map]);

  return null;
}

function RouteMap({ route, selectedSampleIndex, onSelectSample }) {
  const { preferences } = usePreferences();
  const coordinates = route?.route_geojson?.geometry?.coordinates?.map(([longitude, latitude]) => [
    latitude,
    longitude,
  ]) || [[51.505, -0.09]];

  return (
    <div className="map-card">
      <MapContainer className="route-map" center={coordinates[0]} zoom={11} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitToRoute coordinates={coordinates} />
        <Polyline color="#0d6c74" positions={coordinates} weight={4} />

        {route?.sampled_points?.map((point) => {
          const isSelected = point.index === selectedSampleIndex;
          const position = [point.latitude, point.longitude];

          if (isSelected) {
            return (
              <Marker icon={selectedIcon} key={point.index} position={position}>
                <Popup>
                  <div className="popup-stack">
                    <strong>Sample {point.index + 1}</strong>
                    <span>{formatDateTime(point.timestamp, preferences)}</span>
                    <span>{formatDistanceKm(point.distance_from_start_km, preferences)}</span>
                    <span>{point.weather?.summary || "Forecast unavailable"}</span>
                  </div>
                </Popup>
              </Marker>
            );
          }

          return (
            <CircleMarker
              center={position}
              eventHandlers={{ click: () => onSelectSample(point) }}
              fillColor="#dff6f4"
              fillOpacity={1}
              key={point.index}
              pathOptions={{ color: "#0d6c74", weight: 2 }}
              radius={6}
            >
              <Popup>
                <div className="popup-stack">
                  <strong>Sample {point.index + 1}</strong>
                  <span>{formatDateTime(point.timestamp, preferences)}</span>
                  <span>{formatDistanceKm(point.distance_from_start_km, preferences)}</span>
                  <span>{point.weather?.summary || "Forecast unavailable"}</span>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}

export default RouteMap;
