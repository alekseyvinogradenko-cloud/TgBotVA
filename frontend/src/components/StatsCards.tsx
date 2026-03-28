interface Props {
  todo: number;
  inProgress: number;
  done: number;
}

export function StatsCards({ todo, inProgress, done }: Props) {
  const total = todo + inProgress + done;
  const completion = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label="Всего задач" value={total} color="text-gray-700" bg="bg-white" />
      <StatCard label="К выполнению" value={todo} color="text-gray-600" bg="bg-gray-50" />
      <StatCard label="В работе" value={inProgress} color="text-blue-600" bg="bg-blue-50" />
      <StatCard label="Выполнено" value={`${done} (${completion}%)`} color="text-green-600" bg="bg-green-50" />
    </div>
  );
}

function StatCard({ label, value, color, bg }: { label: string; value: string | number; color: string; bg: string }) {
  return (
    <div className={`${bg} rounded-xl p-4 border border-gray-100`}>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  );
}
