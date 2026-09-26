export function riskClass(risk) {
  if (!risk) return ''
  return risk.toLowerCase()
}

export default function RiskBadge({ risk }) {
  if (!risk) return <span className="badge missing">Not evaluated</span>
  return <span className={`badge ${riskClass(risk)}`}>{risk} risk</span>
}

export function StatusBadge({ status }) {
  const cls = status ? status.toLowerCase() : 'missing'
  return <span className={`badge ${cls}`}>{status}</span>
}
