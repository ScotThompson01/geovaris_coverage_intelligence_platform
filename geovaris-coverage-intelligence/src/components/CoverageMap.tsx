"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";

type CoverageMapProps = {
  latitude: number;
  longitude: number;
  siteName: string;
  scenarioId: string;
};

type CoverageRunResponse = {
  status: string;
  coverageRun: {
    id: string;
    site_name: string;
    coverage_geometry: GeoJSON.Geometry;
  } | null;
};

export default function CoverageMap({
  latitude,
  longitude,
  siteName,
  scenarioId,
}: CoverageMapProps) {
  const containerRef =
    useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    /*
     * GeoVaris serves the MapLibre worker explicitly from /public.
     *
     * Keep this configuration because large GeoJSON coverage
     * geometries are parsed and processed by the MapLibre worker.
     */
    maplibregl.setWorkerUrl(
      "/maplibre-gl-worker.mjs",
    );

    const map =
      new maplibregl.Map({
        container:
          containerRef.current,

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

        center: [
          longitude,
          latitude,
        ],

        zoom: 9,
      });

    map.addControl(
      new maplibregl.NavigationControl(),
      "top-right",
    );

    const marker =
      new maplibregl.Marker({
        color: "#6d28d9",
      })
        .setLngLat([
          longitude,
          latitude,
        ])
        .setPopup(
          new maplibregl.Popup({
            offset: 25,
          }).setHTML(
            `<strong>${siteName}</strong><br>${latitude.toFixed(
              4,
            )}, ${longitude.toFixed(
              4,
            )}`,
          ),
        )
        .addTo(map);

    let isActive = true;

    const abortController =
      new AbortController();

    async function loadCoverage(): Promise<void> {
      try {
        const response =
          await fetch(
            `/api/coverage-runs/latest?scenarioId=${encodeURIComponent(
              scenarioId,
            )}`,
            {
              cache: "no-store",
              signal:
                abortController.signal,
            },
          );

        if (!response.ok) {
          throw new Error(
            `Coverage lookup failed with status ${response.status}.`,
          );
        }

        const data =
          (await response.json()) as CoverageRunResponse;

        if (
          !isActive ||
          !data.coverageRun ||
          !data.coverageRun.coverage_geometry
        ) {
          return;
        }

        const coverageFeature:
          GeoJSON.Feature = {
            type: "Feature",

            geometry:
              data.coverageRun
                .coverage_geometry,

            properties: {
              runId:
                data.coverageRun.id,

              siteName:
                data.coverageRun
                  .site_name,
            },
          };

        const existingSource =
          map.getSource(
            "coverage-result",
          ) as
            | maplibregl.GeoJSONSource
            | undefined;

        if (existingSource) {
          existingSource.setData(
            coverageFeature,
          );
        } else {
          map.addSource(
            "coverage-result",
            {
              type: "geojson",
              data: coverageFeature,
            },
          );

          map.addLayer({
            id: "coverage-fill",
            type: "fill",
            source: "coverage-result",

            paint: {
              "fill-color":
                "#7c3aed",

              "fill-opacity":
                0.35,
            },
          });

          map.addLayer({
            id: "coverage-outline",
            type: "line",
            source: "coverage-result",

            paint: {
              "line-color":
                "#4c1d95",

              "line-width":
                3,
            },
          });
        }

        const bounds =
          new maplibregl.LngLatBounds();

        function extendBounds(
          coordinates: unknown,
        ): void {
          if (
            Array.isArray(
              coordinates,
            ) &&
            coordinates.length >= 2 &&
            typeof coordinates[0] ===
              "number" &&
            typeof coordinates[1] ===
              "number"
          ) {
            bounds.extend([
              coordinates[0],
              coordinates[1],
            ]);

            return;
          }

          if (
            Array.isArray(
              coordinates,
            )
          ) {
            coordinates.forEach(
              extendBounds,
            );
          }
        }

        if (
          "coordinates" in
          data.coverageRun
            .coverage_geometry
        ) {
          extendBounds(
            data.coverageRun
              .coverage_geometry
              .coordinates,
          );
        }

        if (!bounds.isEmpty()) {
          map.fitBounds(
            bounds,
            {
              padding: 40,
              maxZoom: 10,
            },
          );
        }
      } catch (error) {
        if (
          abortController.signal
            .aborted
        ) {
          return;
        }

        console.error(
          "Coverage map load failed:",
          error,
        );
      }
    }

    /*
     * Load the completed geometry once when the map is ready.
     *
     * The previous implementation polled every three seconds,
     * which repeatedly transferred the full multi-megabyte
     * coverage geometry.
     */
    map.once(
      "load",
      () => {
        void loadCoverage();
      },
    );

    return () => {
      isActive = false;

      abortController.abort();

      marker.remove();

      map.remove();
    };
  }, [
    latitude,
    longitude,
    siteName,
    scenarioId,
  ]);

  return (
    <div
      ref={containerRef}
      className="h-96 w-full rounded-lg"
      aria-label={`Coverage map for ${siteName}`}
    />
  );
}