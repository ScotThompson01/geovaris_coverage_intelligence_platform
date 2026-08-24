import CoverageMap from "@/components/CoverageMap";
import CreateScenarioForm from "@/components/CreateScenarioForm";
import CreateSiteForm from "@/components/CreateSiteForm";
import CreateCoverageRunButton from "@/components/CreateCoverageRunButton";
import { sql } from "@/lib/db";

type ScenarioRow = {
  scenario_id: string;
  customer_name: string;
  project_name: string;
  site_name: string;
  latitude: number;
  longitude: number;
  scenario_name: string;
  frequency_mhz: number;
  eirp_watts: number;
  antenna_height_m: number;
  receiver_threshold_dbm: number;
  propagation_model: string;
};

export default async function Home() {
  const rows = (await sql`
    SELECT
      c.name AS customer_name,
      p.name AS project_name,
      s.name AS site_name,
      s.latitude,
      s.longitude,
      sc.id AS scenario_id,
      sc.name AS scenario_name,
      sc.frequency_mhz,
      sc.eirp_watts,
      sc.antenna_height_m,
      sc.receiver_threshold_dbm,
      sc.propagation_model
    FROM customers c
    JOIN projects p
      ON p.customer_id = c.id
    JOIN sites s
      ON s.project_id = p.id
      AND s.customer_id = c.id
    JOIN scenarios sc
      ON sc.site_id = s.id
      AND sc.customer_id = c.id
    ORDER BY sc.created_at DESC
    LIMIT 1;
  `) as unknown as ScenarioRow[];

  const scenario = rows[0];

  if (!scenario) {
    return (
      <main className="min-h-screen bg-slate-50">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto max-w-7xl px-6 py-5">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              GeoVaris Coverage Intelligence
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              Clean data. Confident results.
            </p>
          </div>
        </header>

        <div className="mx-auto max-w-7xl px-6 py-8">
          <p className="text-slate-600">
            No coverage scenario data was found.
          </p>

          <section className="mt-8">
            <CreateSiteForm />
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
                GeoVaris Coverage Intelligence
              </h1>

              <p className="mt-1 text-sm text-slate-500">
                Clean data. Confident results.
              </p>
            </div>

            <div className="rounded-full bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">
              Development
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <section className="mb-8">
          <p className="text-sm font-medium uppercase tracking-wide text-indigo-600">
            Coverage Scenario
          </p>

          <h2 className="mt-2 text-3xl font-semibold text-slate-900">
            {scenario.site_name}
          </h2>

          <p className="mt-2 text-slate-600">
            {scenario.customer_name}
            {" · "}
            {scenario.project_name}
            {" · "}
            {scenario.scenario_name}
          </p>
        </section>

        <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Frequency"
            value={`${scenario.frequency_mhz} MHz`}
          />

          <MetricCard
            label="EIRP"
            value={`${scenario.eirp_watts.toLocaleString()} W`}
          />

          <MetricCard
            label="Antenna Height"
            value={`${scenario.antenna_height_m} m`}
          />

          <MetricCard
            label="Receiver Threshold"
            value={`${scenario.receiver_threshold_dbm} dBm`}
          />
        </section>

        <section className="mt-6">
          <CreateCoverageRunButton
            scenarioId={scenario.scenario_id}
          />
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                Coverage Map
              </h3>

              <p className="mt-1 text-sm text-slate-500">
                Interactive site and RF coverage visualization.
              </p>
            </div>

            <div className="mt-6 overflow-hidden rounded-lg border border-slate-200">
              <CoverageMap
                latitude={scenario.latitude}
                longitude={scenario.longitude}
                siteName={scenario.site_name}
              />
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">
              Site Details
            </h3>

            <dl className="mt-6 space-y-5">
              <DetailRow
                label="Latitude"
                value={scenario.latitude.toFixed(4)}
              />

              <DetailRow
                label="Longitude"
                value={scenario.longitude.toFixed(4)}
              />

              <DetailRow
                label="Propagation Model"
                value={scenario.propagation_model}
              />

              <DetailRow
                label="Scenario"
                value={scenario.scenario_name}
              />

              <DetailRow
                label="Project"
                value={scenario.project_name}
              />
            </dl>
          </div>
        </section>

        <section className="mt-8">
          <CreateSiteForm />
        </section>

        <section className="mt-8">
          <CreateScenarioForm />
        </section>

      </div>
    </main>
  );
}

type MetricCardProps = {
  label: string;
  value: string;
};

function MetricCard({ label, value }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-sm font-medium text-slate-500">
        {label}
      </p>

      <p className="mt-2 text-2xl font-semibold text-slate-900">
        {value}
      </p>
    </div>
  );
}

type DetailRowProps = {
  label: string;
  value: string;
};

function DetailRow({ label, value }: DetailRowProps) {
  return (
    <div>
      <dt className="text-sm text-slate-500">
        {label}
      </dt>

      <dd className="mt-1 font-medium text-slate-900">
        {value}
      </dd>
    </div>
  );
}