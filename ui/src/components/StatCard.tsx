type StatCardProps = {
  label: string;
  value: number | string;
  hint?: string;
};

export const StatCard = ({ label, value, hint }: StatCardProps) => (
  <div className="card p-4 transition hover:-translate-y-0.5">
    <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
    <h3 className="mt-2 text-2xl font-semibold text-slate-100">{value}</h3>
    {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
  </div>
);
