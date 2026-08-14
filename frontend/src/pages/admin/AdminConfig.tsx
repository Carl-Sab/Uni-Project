import { useEffect, useState } from "react";
import { Check, Save } from "lucide-react";
import { useAdminConfig, useUpdateAdminConfig } from "../../lib/adminQueries";
import { AdminButton, AdminCard } from "../../components/admin/ui";

const MODEL_OPTIONS = [
  { value: "anthropic|claude-sonnet-4-5", label: "Claude Sonnet 4.5" },
  { value: "openai|gpt-5", label: "GPT-5" },
  { value: "google|gemini-3-flash", label: "Gemini 3 Flash" },
];

export default function AdminConfig() {
  const { data: config, isLoading } = useAdminConfig();
  const update = useUpdateAdminConfig();

  const [persona, setPersona] = useState("");
  const [modelKey, setModelKey] = useState(MODEL_OPTIONS[0].value);
  const [responseLength, setResponseLength] = useState<"brief" | "detailed">("detailed");
  const [temperature, setTemperature] = useState(0.3);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!config) return;
    setPersona(config.persona);
    setModelKey(`${config.model_provider}|${config.model_name}`);
    setResponseLength(config.response_length);
    setTemperature(parseFloat(config.temperature));
  }, [config]);

  async function handleSave() {
    const [model_provider, model_name] = modelKey.split("|");
    await update.mutateAsync({
      persona,
      model_provider,
      model_name,
      response_length: responseLength,
      temperature: temperature.toFixed(1),
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (isLoading) return <p className="text-sm text-steel-400">Loading…</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-steel-900">Assistant Configuration</h1>
        <p className="mt-0.5 text-sm text-steel-500">
          Changes apply to the very next chat message - no restart needed.
        </p>
      </div>

      <AdminCard className="space-y-5 p-5">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-steel-500">Persona / tone</label>
          <textarea
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            rows={3}
            placeholder="e.g. friendly and encouraging, but precise about policy"
            className="w-full resize-none rounded-md border border-steel-200 px-3 py-2 text-sm text-steel-800 placeholder:text-steel-400 focus:border-steel-400 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-steel-500">Model</label>
            <select
              value={modelKey}
              onChange={(e) => setModelKey(e.target.value)}
              className="w-full rounded-md border border-steel-200 px-3 py-2 text-sm text-steel-800 focus:border-steel-400 focus:outline-none"
            >
              {MODEL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-steel-500">Response length</label>
            <select
              value={responseLength}
              onChange={(e) => setResponseLength(e.target.value as "brief" | "detailed")}
              className="w-full rounded-md border border-steel-200 px-3 py-2 text-sm text-steel-800 focus:border-steel-400 focus:outline-none"
            >
              <option value="brief">Brief</option>
              <option value="detailed">Detailed</option>
            </select>
          </div>
        </div>

        <div>
          <label className="mb-1.5 flex items-center justify-between text-xs font-medium text-steel-500">
            <span>Temperature</span>
            <span className="tabular-nums text-steel-700">{temperature.toFixed(1)}</span>
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="w-full accent-steel-600"
          />
          <div className="flex justify-between text-[11px] text-steel-400">
            <span>Precise</span>
            <span>Creative</span>
          </div>
        </div>

        <div className="flex items-center gap-3 border-t border-steel-100 pt-4">
          <AdminButton onClick={handleSave} disabled={update.isPending}>
            <Save className="size-3.5" />
            {update.isPending ? "Saving…" : "Save changes"}
          </AdminButton>
          {saved && (
            <span className="flex items-center gap-1 text-sm text-good-500">
              <Check className="size-3.5" /> Saved
            </span>
          )}
        </div>
      </AdminCard>
    </div>
  );
}
