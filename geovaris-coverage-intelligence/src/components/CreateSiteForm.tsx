"use client";

import { FormEvent, useEffect, useState } from "react";

type Project = {
  id: string;
  name: string;
  customer_name: string;
};

type SiteResponse = {
  status?: string;
  error?: string;
  site?: {
    id: string;
    name: string;
    latitude: number;
    longitude: number;
  };
};

export default function CreateSiteForm() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [name, setName] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");

  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProjects() {
      try {
        const response =
          await fetch(
            "/api/projects?access=write",
          );
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error ?? "Unable to load projects.");
        }

        setProjects(data.projects ?? []);

        if (data.projects?.length > 0) {
          setProjectId(data.projects[0].id);
        }
      } catch (err) {
        console.error(err);
        setError("Unable to load projects.");
      } finally {
        setIsLoadingProjects(false);
      }
    }

    loadProjects();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setMessage("");
    setError("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/sites", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          projectId,
          name,
          latitude: Number(latitude),
          longitude: Number(longitude),
        }),
      });

      const data = (await response.json()) as SiteResponse;

      if (!response.ok) {
        throw new Error(data.error ?? "Unable to create site.");
      }

      setMessage(`Site ${data.site?.name ?? name} created successfully.`);

      setName("");
      setLatitude("");
      setLongitude("");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to create site.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">
          Create Site
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Add a site location to a GeoVaris project.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-5"
      >
        <div>
          <label
            htmlFor="project"
            className="block text-sm font-medium text-slate-700"
          >
            Project
          </label>

          <select
            id="project"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            disabled={isLoadingProjects}
            required
            className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900"
          >
            {isLoadingProjects && (
              <option value="">Loading projects...</option>
            )}

            {!isLoadingProjects && projects.length === 0 && (
              <option value="">No projects available</option>
            )}

            {projects.map((project) => (
              <option
                key={project.id}
                value={project.id}
              >
                {project.customer_name} — {project.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="site-name"
            className="block text-sm font-medium text-slate-700"
          >
            Site Name
          </label>

          <input
            id="site-name"
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Example: ORL-124"
            required
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="latitude"
              className="block text-sm font-medium text-slate-700"
            >
              Latitude
            </label>

            <input
              id="latitude"
              type="number"
              step="any"
              min="-90"
              max="90"
              value={latitude}
              onChange={(event) => setLatitude(event.target.value)}
              placeholder="28.5383"
              required
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="longitude"
              className="block text-sm font-medium text-slate-700"
            >
              Longitude
            </label>

            <input
              id="longitude"
              type="number"
              step="any"
              min="-180"
              max="180"
              value={longitude}
              onChange={(event) => setLongitude(event.target.value)}
              placeholder="-81.3792"
              required
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
            />
          </div>
        </div>

        {message && (
          <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
            {message}
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={
            isSubmitting ||
            isLoadingProjects ||
            !projectId
          }
          className="w-full rounded-lg bg-indigo-700 px-4 py-2.5 font-medium text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Creating Site..." : "Create Site"}
        </button>
      </form>
    </div>
  );
}