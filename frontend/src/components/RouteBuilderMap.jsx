import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";

function ClickCapture({ onAddWaypoint }) {
  useMapEvents({
    click(event) {
      onAddWaypoint({
        latitude: Number(event.latlng.lat.toFixed(6)),
        longitude: Number(event.latlng.lng.toFixed(6)),
      });
    },
  });

  return null;
}

function FitToManualRoute({ previewCoordinates, waypoints }) {
  const map = useMap();

  useEffect(() => {
    const positions = previewCoordinates.length
      ? previewCoordinates
      : waypoints.map((point) => [point.latitude, point.longitude]);

    if (!positions.length) {
      return;
    }

    if (positions.length === 1) {
      map.setView(positions[0], 12);
      return;
    }

    map.fitBounds(positions, { padding: [24, 24] });
  }, [map, previewCoordinates, waypoints]);

  return null;
}

function RouteBuilderMap({ mode, waypoints, previewGeojson, onAddWaypoint }) {
  const previewCoordinates = previewGeojson?.geometry?.coordinates?.map(([longitude, latitude]) => [
    latitude,
    longitude,
  ]) || [];

  return (
    <div className="map-card">
      <MapContainer center={[51.505, -0.09]} className="route-map route-builder-map" zoom={11} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickCapture onAddWaypoint={onAddWaypoint} />
        <FitToManualRoute previewCoordinates={previewCoordinates} waypoints={waypoints} />

        {previewCoordinates.length ? (
          <Polyline color="#0d6c74" positions={previewCoordinates} weight={4} />
        ) : null}

        {waypoints.map((point, index) => (
          <CircleMarker
            center={[point.latitude, point.longitude]}
            fillColor={mode === "endpoints" && index === 0 ? "#138c84" : "#ff8f4f"}
            fillOpacity={1}
            key={`${point.latitude}-${point.longitude}-${index}`}
            pathOptions={{ color: "#ffffff", weight: 3 }}
            radius={9}
          >
            <Tooltip direction="top" offset={[0, -8]} permanent>
              {mode === "endpoints" && index === 0
                ? "Start"
                : mode === "endpoints" && index === 1
                  ? "Finish"
                  : `Point ${index + 1}`}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}

export default RouteBuilderMap;
