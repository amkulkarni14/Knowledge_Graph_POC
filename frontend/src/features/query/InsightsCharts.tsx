import { useEffect, useRef, useState } from "react";
import { Button, Tooltip } from "@mui/material";
import { DataTable } from "../../shared/ui/WorkspaceUi";
import type { JsonObject, Schema } from "../../types/common.types";

type Bucket = Schema<"InsightsBucket">;
const formatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
const categoryColors = ["#426e94", "#7892aa", "#6d9693", "#a29ab0", "#b79d81", "#58677b"];
export const formatMetric = (value?: number | null) =>
  value == null ? "Unavailable" : formatter.format(value);

export function MetricCards({ metrics }: { metrics: Schema<"InsightsMetric">[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
      {metrics.map(({ label, value, definition, unit }) => (
        <Tooltip key={label} title={definition}>
          <div tabIndex={0} className="panel min-w-0">
            <p className="muted break-words">{label}</p>
            <strong className="text-lg">{formatMetric(value)}{value != null && unit ? (unit === "%" ? unit : " " + unit) : ""}</strong>
            <p className="hidden print:block text-xs">{definition}</p>
          </div>
        </Tooltip>
      ))}
    </div>
  );
}

export function AggregateTable({ rows }: { rows: JsonObject[] }) {
  const [offset, setOffset] = useState(0);
  const page = Math.min(offset, Math.max(0, Math.ceil(rows.length / 25) - 1) * 25);
  return (
    <DataTable rows={rows.slice(page, page + 25)} offset={page}
      total={rows.length} onPage={rows.length > 25 ? setOffset : undefined} />
  );
}

export function Bars({ rows, onSelect, active }: {
  rows: Bucket[];
  onSelect?: (label: string) => void;
  active?: string | null;
}) {
  const max = Math.max(1, ...rows.map((row) => row.records));
  return (
    <ul className="grid gap-3">
      {rows.map(({ label, records }) => (
        <li key={label}>
          {onSelect ? (
            <Button aria-pressed={active === label} onClick={() => onSelect(label)}
              size="small" sx={{ textTransform: "none" }}>{label} · {formatMetric(records)}</Button>
          ) : <div className="text-sm break-words">{label} · {formatMetric(records)}</div>}
          <div aria-hidden="true" className="h-2 rounded bg-slate-100">
            <div className="h-full rounded bg-slate-500" style={{ width: (records / max * 100) + "%" }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function CategoryDonut({ rows }: { rows: Bucket[] }) {
  const total = rows.reduce((sum, row) => sum + row.records, 0);
  let start = 0;
  const wedges = rows.map(({ records }, index) => {
    const end = start + records / total * 100;
    const wedge = categoryColors[index] + " " + start + "% " + end + "%";
    start = end;
    return wedge;
  });
  return (
    <div className="flex items-center gap-4 mb-4">
      <div aria-hidden="true" className="relative rounded-full size-24 shrink-0"
        style={{ background: "conic-gradient(" + wedges.join(", ") + ")" }}>
        <div className="absolute inset-5 rounded-full bg-white" />
      </div>
      <ul className="grid gap-1 text-sm">
        {rows.map(({ label, records }, index) => (
          <li key={label} className="flex items-center gap-2 break-words">
            <span aria-hidden="true" className="size-2 rounded-full shrink-0" style={{ backgroundColor: categoryColors[index] }} />
            {label} · {formatMetric(records / total * 100)}%
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PerformanceBars({ rows }: { rows: Bucket[] }) {
  const maximum = Math.max(1, ...rows.map(({ total }) => Math.abs(total ?? 0)));
  const hasNegative = rows.some(({ total }) => (total ?? 0) < 0);
  const zero = hasNegative ? 50 : 0;
  return (
    <ul className="grid gap-3 mb-3">
      {rows.map(({ label, total }) => {
        const width = Math.abs(total ?? 0) / maximum * (100 - zero);
        return (
          <li key={label}>
            <div className="text-sm break-words">{label} · {formatMetric(total)}</div>
            <div aria-hidden="true" className="relative h-2 rounded bg-slate-100">
              <div className="absolute h-full rounded bg-slate-500"
                style={{ width: width + "%", left: (total != null && total < 0 ? zero - width : zero) + "%" }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function downloadFile(href: string, name: string) {
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  link.click();
}

function drawTrend(canvas: HTMLCanvasElement, rows: Bucket[], context: string, amount: string) {
  const g = canvas.getContext("2d");
  if (!g) return;
  const { width, height } = canvas;
  const points = rows.map((row) => amount === "Records" ? row.records : row.total);
  const values = points.filter((v): v is number => v != null);
  const min = Math.min(0, ...values);
  const max = Math.max(min + 1, ...values);
  const y = (v: number) => 184 - ((v - min) / (max - min)) * 112;
  const x = (i: number) => 74 + i * (width - 120) / Math.max(1, rows.length - 1);
  g.fillStyle = "#ffffff";
  g.fillRect(0, 0, width, height);
  g.fillStyle = "#334155";
  g.font = "16px sans-serif";
  g.fillText(context, 20, 24, width - 40);
  g.font = "13px sans-serif";
  g.fillText(amount, 20, 46);
  for (const value of [min, (min + max) / 2, max]) {
    g.fillStyle = "#475569";
    g.fillText(formatMetric(value), 12, y(value) + 4, 58);
    g.strokeStyle = "#e2e8f0";
    g.beginPath();
    g.moveTo(70, y(value));
    g.lineTo(width - 32, y(value));
    g.stroke();
  }
  g.strokeStyle = "#426e94";
  if (points.length > 1 && points.every((value) => value != null && value >= 0)) {
    g.fillStyle = "#e4edf5";
    g.beginPath();
    g.moveTo(x(0), y(0));
    points.forEach((value, index) => g.lineTo(x(index), y(value ?? 0)));
    g.lineTo(x(points.length - 1), y(0));
    g.closePath();
    g.fill();
  }
  g.fillStyle = "#426e94";
  g.lineWidth = 2.5;
  points.forEach((value, index) => {
    if (value == null) return;
    const previous = points[index - 1];
    if (previous != null) {
      g.beginPath();
      g.moveTo(x(index - 1), y(previous));
      g.lineTo(x(index), y(value));
      g.stroke();
    }
    g.beginPath();
    g.arc(x(index), y(value), 3, 0, Math.PI * 2);
    g.fill();
  });
  g.fillStyle = "#475569";
  g.fillText(rows[0].label, 70, 212);
  if (rows.length > 1) {
    g.textAlign = "right";
    g.fillText(rows.at(-1)!.label, width - 32, 212);
    g.textAlign = "left";
  }
}

export function TrendChart({ rows, context, measure }: { rows: Bucket[]; context: string; measure?: string | null }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [showTotal, setShowTotal] = useState(false);
  const amount = showTotal && measure && rows.some(({ total }) => total != null) ? "Total " + measure : "Records";
  useEffect(() => {
    if (canvas.current) drawTrend(canvas.current, rows, context, amount);
  }, [rows, context, amount]);
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {measure && rows.some(({ total }) => total != null) && (
          <Button size="small" onClick={() => setShowTotal(!showTotal)}>
            {amount === "Records" ? "Show measure totals" : "Show record counts"}
          </Button>
        )}
        <Button size="small" onClick={() => {
          if (canvas.current) downloadFile(canvas.current.toDataURL("image/png"), "business-trends.png");
        }}>Download chart PNG</Button>
      </div>
      <canvas ref={canvas} width={774} height={232} className="w-full"
        role="img" aria-label={amount + " over observed periods. Values are in the aggregate table below."} />
      <AggregateTable rows={rows} />
    </>
  );
}

export function exportInsights(data: Schema<"InsightsResponse">, workspace: string, filters: object) {
  const rows: (string | number | null | undefined)[][] = [
    ["workspace", workspace], ["source", data.source], ["dataset", data.table],
    ["refreshed UTC", data.refreshed_at], ["requested filters", JSON.stringify(filters)],
    ["analyzed rows", data.scanned], ["bounded result", String(data.truncated)],
    ["metric", "value", "unit", "definition"],
    ...[...data.metrics, ...(data.graph?.metrics ?? [])].map((m) => [m.label, m.value, m.unit, m.definition]),
    ["section", "group", "records", "total"],
    ...([["category", data.distribution], ["period", data.trends],
      ["entity type", data.graph?.entities ?? []], ["relationship type", data.graph?.relationships ?? []],
      ["component size", data.graph?.communities ?? []], ["dependency", data.graph?.dependencies ?? []]] as [string, Bucket[]][]).flatMap(
        ([section, buckets]) => buckets.map((b) => [section, b.label, b.records, b.total]),
      ),
    ["dataset", "quality issue", "count", "severity"],
    ...data.quality.map((issue) => [issue.dataset, issue.issue, issue.count, issue.severity]),
  ];
  const csv = rows.map((row) => row.map((cell) => {
    const value = String(cell ?? "");
    const safe = typeof cell === "string" && /^[\s\uFEFF]*[=+\-@\t\r]/.test(value) ? "'" + value : value;
    return '"' + safe.replaceAll('"', '""') + '"';
  }).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  downloadFile(url, "business-insights.csv");
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
