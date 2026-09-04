"use client";

import {
    useEffect,
    useRef,
    useState,
} from "react";

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
        coverage_geometry:
            GeoJSON.Geometry;
    } | null;
};

type LocationPoint = {
    id: string;
    latitude: number;
    longitude: number;
    covered: boolean;
};

type LocationDataset = {
    id: string;
    name: string;
    type: string;
    isMock: boolean;
    totalLocations:
        | number
        | null;
};

type LocationPointResponse = {
    status: string;

    dataset:
        | LocationDataset
        | null;

    points:
        LocationPoint[];

    error?: string;
};

const COVERAGE_SOURCE_ID =
    "coverage-result";

const LOCATION_SOURCE_ID =
    "coverage-location-points";

const LOCATION_UNCOVERED_LAYER_ID =
    "location-points-uncovered";

const LOCATION_COVERED_LAYER_ID =
    "location-points-covered";

export default function CoverageMap({
    latitude,
    longitude,
    siteName,
    scenarioId,
}: CoverageMapProps) {
    const containerRef =
        useRef<HTMLDivElement | null>(
            null,
        );

    const mapRef =
        useRef<maplibregl.Map | null>(
            null,
        );

    const [
        showLocations,
        setShowLocations,
    ] = useState(true);

    const [
        locationDataset,
        setLocationDataset,
    ] = useState<LocationDataset | null>(
        null,
    );

    const [
        coveredLocationCount,
        setCoveredLocationCount,
    ] = useState(0);

    const [
        locationError,
        setLocationError,
    ] = useState("");

    useEffect(() => {
        if (!containerRef.current) {
            return;
        }

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
                            type:
                                "raster",

                            tiles: [
                                "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                            ],

                            tileSize:
                                256,

                            attribution:
                                "&copy; OpenStreetMap contributors",
                        },
                    },

                    layers: [
                        {
                            id:
                                "openStreetMap",

                            type:
                                "raster",

                            source:
                                "openStreetMap",
                        },
                    ],
                },

                center: [
                    longitude,
                    latitude,
                ],

                zoom:
                    9,
            });

        mapRef.current =
            map;

        map.addControl(
            new maplibregl.NavigationControl(),
            "top-right",
        );

        const marker =
            new maplibregl.Marker({
                color:
                    "#6d28d9",
            })
                .setLngLat([
                    longitude,
                    latitude,
                ])
                .setPopup(
                    new maplibregl.Popup({
                        offset:
                            25,
                    }).setHTML(
                        `<strong>${siteName}</strong><br>${latitude.toFixed(
                            4,
                        )}, ${longitude.toFixed(
                            4,
                        )}`,
                    ),
                )
                .addTo(map);

        let isActive =
            true;

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
                            cache:
                                "no-store",

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
                    !data.coverageRun
                        .coverage_geometry
                ) {
                    return;
                }

                const coverageFeature:
                    GeoJSON.Feature = {
                        type:
                            "Feature",

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
                        COVERAGE_SOURCE_ID,
                    ) as
                        | maplibregl.GeoJSONSource
                        | undefined;

                if (existingSource) {
                    existingSource.setData(
                        coverageFeature,
                    );
                } else {
                    map.addSource(
                        COVERAGE_SOURCE_ID,
                        {
                            type:
                                "geojson",

                            data:
                                coverageFeature,
                        },
                    );

                    map.addLayer({
                        id:
                            "coverage-fill",

                        type:
                            "fill",

                        source:
                            COVERAGE_SOURCE_ID,

                        paint: {
                            "fill-color":
                                "#7c3aed",

                            "fill-opacity":
                                0.35,
                        },
                    });

                    map.addLayer({
                        id:
                            "coverage-outline",

                        type:
                            "line",

                        source:
                            COVERAGE_SOURCE_ID,

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
                        coordinates.length >=
                            2 &&
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
                            padding:
                                50,

                            maxZoom:
                                10,
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

        async function loadLocationPoints(): Promise<void> {
            try {
                const response =
                    await fetch(
                        `/api/coverage-runs/location-points?scenarioId=${encodeURIComponent(
                            scenarioId,
                        )}`,
                        {
                            cache:
                                "no-store",

                            signal:
                                abortController.signal,
                        },
                    );

                const data =
                    (await response.json()) as LocationPointResponse;

                if (!response.ok) {
                    throw new Error(
                        data.error ??
                            "Unable to load location points.",
                    );
                }

                if (!isActive) {
                    return;
                }

                setLocationDataset(
                    data.dataset,
                );

                setCoveredLocationCount(
                    data.points.filter(
                        (point) =>
                            point.covered,
                    ).length,
                );

                setLocationError(
                    "",
                );

                if (
                    !data.dataset ||
                    data.points.length ===
                        0
                ) {
                    return;
                }

                const pointFeatures:
                    GeoJSON.Feature<
                        GeoJSON.Point,
                        {
                            id:
                                string;

                            covered:
                                boolean;
                        }
                    >[] =
                    data.points.map(
                        (point) => ({
                            type:
                                "Feature",

                            geometry: {
                                type:
                                    "Point",

                                coordinates: [
                                    point.longitude,
                                    point.latitude,
                                ],
                            },

                            properties: {
                                id:
                                    point.id,

                                covered:
                                    point.covered,
                            },
                        }),
                    );

                const featureCollection:
                    GeoJSON.FeatureCollection<
                        GeoJSON.Point,
                        {
                            id:
                                string;

                            covered:
                                boolean;
                        }
                    > = {
                        type:
                            "FeatureCollection",

                        features:
                            pointFeatures,
                    };

                const existingSource =
                    map.getSource(
                        LOCATION_SOURCE_ID,
                    ) as
                        | maplibregl.GeoJSONSource
                        | undefined;

                if (existingSource) {
                    existingSource.setData(
                        featureCollection,
                    );

                    return;
                }

                map.addSource(
                    LOCATION_SOURCE_ID,
                    {
                        type:
                            "geojson",

                        data:
                            featureCollection,
                    },
                );

                map.addLayer({
                    id:
                        LOCATION_UNCOVERED_LAYER_ID,

                    type:
                        "circle",

                    source:
                        LOCATION_SOURCE_ID,

                    filter: [
                        "==",
                        [
                            "get",
                            "covered",
                        ],
                        false,
                    ],

                    layout: {
                        visibility:
                            showLocations
                                ? "visible"
                                : "none",
                    },

                    paint: {
                        "circle-radius":
                            4,

                        "circle-color":
                            "#64748b",

                        "circle-opacity":
                            0.65,

                        "circle-stroke-color":
                            "#ffffff",

                        "circle-stroke-width":
                            1,
                    },
                });

                map.addLayer({
                    id:
                        LOCATION_COVERED_LAYER_ID,

                    type:
                        "circle",

                    source:
                        LOCATION_SOURCE_ID,

                    filter: [
                        "==",
                        [
                            "get",
                            "covered",
                        ],
                        true,
                    ],

                    layout: {
                        visibility:
                            showLocations
                                ? "visible"
                                : "none",
                    },

                    paint: {
                        "circle-radius":
                            5,

                        "circle-color":
                            "#16a34a",

                        "circle-opacity":
                            0.9,

                        "circle-stroke-color":
                            "#ffffff",

                        "circle-stroke-width":
                            1.5,
                    },
                });
            } catch (error) {
                if (
                    abortController.signal
                        .aborted
                ) {
                    return;
                }

                console.error(
                    "Location point map load failed:",
                    error,
                );

                if (isActive) {
                    setLocationError(
                        "Unable to load location points.",
                    );
                }
            }
        }

        map.once(
            "load",
            () => {
                void loadCoverage();
                void loadLocationPoints();
            },
        );

        return () => {
            isActive =
                false;

            abortController.abort();

            marker.remove();

            mapRef.current =
                null;

            map.remove();
        };
    }, [
        latitude,
        longitude,
        siteName,
        scenarioId,
        showLocations,
    ]);

    useEffect(() => {
        const map =
            mapRef.current;

        if (!map) {
            return;
        }

        const visibility =
            showLocations
                ? "visible"
                : "none";

        if (
            map.getLayer(
                LOCATION_UNCOVERED_LAYER_ID,
            )
        ) {
            map.setLayoutProperty(
                LOCATION_UNCOVERED_LAYER_ID,
                "visibility",
                visibility,
            );
        }

        if (
            map.getLayer(
                LOCATION_COVERED_LAYER_ID,
            )
        ) {
            map.setLayoutProperty(
                LOCATION_COVERED_LAYER_ID,
                "visibility",
                visibility,
            );
        }
    }, [
        showLocations,
    ]);

    return (
        <div className="relative">
            <div
                ref={
                    containerRef
                }
                className="h-[600px] w-full rounded-lg"
                aria-label={`Coverage map for ${siteName}`}
            />

            {locationDataset ? (
                <div className="absolute left-4 top-4 z-10 max-w-xs rounded-lg border border-slate-200 bg-white/95 p-3 shadow-md backdrop-blur">
                    <label className="flex cursor-pointer items-center gap-3">
                        <input
                            type="checkbox"
                            checked={
                                showLocations
                            }
                            onChange={
                                (event) =>
                                    setShowLocations(
                                        event.target.checked,
                                    )
                            }
                            className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
                        />

                        <span className="text-sm font-medium text-slate-800">
                            {locationDataset.isMock
                                ? "Show Mock Fabric Locations"
                                : "Show Fabric Locations"}
                        </span>
                    </label>

                    <div className="mt-2 border-t border-slate-100 pt-2 text-xs text-slate-600">
                        <p>
                            <span className="font-semibold text-green-700">
                                {coveredLocationCount.toLocaleString()}
                            </span>
                            {" "}
                            covered
                        </p>

                        <p>
                            {locationDataset.totalLocations?.toLocaleString() ??
                                "—"}{" "}
                            total locations
                        </p>

                        {locationDataset.isMock ? (
                            <p className="mt-1 font-medium text-amber-700">
                                Mock / synthetic test data
                            </p>
                        ) : null}
                    </div>
                </div>
            ) : null}

            {locationError ? (
                <div className="absolute bottom-4 left-4 z-10 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 shadow">
                    {locationError}
                </div>
            ) : null}

            {locationDataset &&
            showLocations ? (
                <div className="absolute bottom-4 left-4 z-10 rounded-lg border border-slate-200 bg-white/95 px-3 py-2 text-xs text-slate-700 shadow-md backdrop-blur">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5">
                            <span className="h-3 w-3 rounded-full bg-green-600 ring-1 ring-white" />
                            Covered
                        </span>

                        <span className="flex items-center gap-1.5">
                            <span className="h-3 w-3 rounded-full bg-slate-500 ring-1 ring-white" />
                            Not covered
                        </span>
                    </div>
                </div>
            ) : null}
        </div>
    );
}