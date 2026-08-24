"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";

type CoverageMapProps = {
  latitude: number;
  longitude: number;
  siteName: string;
};

export default function CoverageMap({
  latitude,
  longitude,
  siteName,
}: CoverageMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,

      style: {
        version: 8,
        sources: {
          openStreetMap: {
            type: "raster",
            tiles: [
              "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            ],
            tileSize: 256,
            attribution:
              "&copy; OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "openStreetMap",
            type: "raster",
            source: "openStreetMap",
          },
        ],
      },

      center: [longitude, latitude],
      zoom: 10,
    });

    map.addControl(
      new maplibregl.NavigationControl(),
      "top-right",
    );

    const marker = new maplibregl.Marker({
      color: "#6d28d9",
    })
      .setLngLat([longitude, latitude])
      .setPopup(
        new maplibregl.Popup({
          offset: 25,
        }).setHTML(
          `<strong>${siteName}</strong><br/>${latitude.toFixed(
            4,
          )}, ${longitude.toFixed(4)}`,
        ),
      )
      .addTo(map);

    mapRef.current = map;

    return () => {
      marker.remove();
      map.remove();
      mapRef.current = null;
    };
  }, [latitude, longitude, siteName]);

  return (
    <div
      ref={mapContainerRef}
      className="h-96 w-full rounded-lg"
      aria-label={`Map showing ${siteName}`}
    />
  );
}