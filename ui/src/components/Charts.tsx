import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

import type { CountPoint, TimePoint } from 'types/api';
import { formatChartLabel, titleCase } from 'utils/format';

const AXIS = { stroke: '#5C6679', fontSize: 11 };
const GRID = '#1E2534';

const tooltipStyle = {
  contentStyle: {
    background: '#131822',
    border: '1px solid #2A3345',
    borderRadius: 8,
    fontSize: 12,
    color: '#E7EBF3'
  },
  labelStyle: { color: '#8B95A9', fontSize: 11 },
  cursor: { fill: 'rgba(110,123,255,0.06)' }
} as const;

const SERIES_COLORS = ['#6E7BFF', '#FF5C7A', '#F5C451', '#5AC8FA', '#FF9556', '#4ADE80'];

export const ErrorTrendChart = ({ data }: { data: TimePoint[] }) => (
  <ResponsiveContainer width="100%" height={260}>
    <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
      <defs>
        <linearGradient id="totalFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6E7BFF" stopOpacity={0.35} />
          <stop offset="100%" stopColor="#6E7BFF" stopOpacity={0} />
        </linearGradient>
        <linearGradient id="errorFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FF5C7A" stopOpacity={0.4} />
          <stop offset="100%" stopColor="#FF5C7A" stopOpacity={0} />
        </linearGradient>
      </defs>
      <CartesianGrid stroke={GRID} vertical={false} />
      <XAxis dataKey="bucket" tickFormatter={formatChartLabel} tickLine={false} axisLine={false} {...AXIS} />
      <YAxis allowDecimals={false} tickLine={false} axisLine={false} {...AXIS} />
      <Tooltip {...tooltipStyle} labelFormatter={(value) => formatChartLabel(String(value))} />
      <Legend wrapperStyle={{ fontSize: 11, color: '#8B95A9' }} />
      <Area
        type="monotone"
        dataKey="total"
        name="All events"
        stroke="#6E7BFF"
        strokeWidth={1.5}
        fill="url(#totalFill)"
      />
      <Area
        type="monotone"
        dataKey="errors"
        name="Errors"
        stroke="#FF5C7A"
        strokeWidth={1.5}
        fill="url(#errorFill)"
      />
    </AreaChart>
  </ResponsiveContainer>
);

export const IncidentsOverTimeChart = ({ data }: { data: CountPoint[] }) => (
  <ResponsiveContainer width="100%" height={220}>
    <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
      <CartesianGrid stroke={GRID} vertical={false} />
      <XAxis dataKey="key" tickLine={false} axisLine={false} {...AXIS} />
      <YAxis allowDecimals={false} tickLine={false} axisLine={false} {...AXIS} />
      <Tooltip {...tooltipStyle} />
      <Bar dataKey="count" name="Incidents" fill="#6E7BFF" radius={[3, 3, 0, 0]} maxBarSize={28} />
    </BarChart>
  </ResponsiveContainer>
);

export const HorizontalCountChart = ({ data }: { data: CountPoint[] }) => (
  <ResponsiveContainer width="100%" height={Math.max(180, data.length * 34)}>
    <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
      <CartesianGrid stroke={GRID} horizontal={false} />
      <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} {...AXIS} />
      <YAxis
        type="category"
        dataKey="key"
        width={130}
        tickLine={false}
        axisLine={false}
        tickFormatter={(value: string) => (value.length > 20 ? `${value.slice(0, 19)}…` : value)}
        {...AXIS}
      />
      <Tooltip {...tooltipStyle} />
      <Bar dataKey="count" name="Errors" radius={[0, 3, 3, 0]} maxBarSize={18}>
        {data.map((entry, index) => (
          <Cell key={entry.key} fill={SERIES_COLORS[index % SERIES_COLORS.length]} />
        ))}
      </Bar>
    </BarChart>
  </ResponsiveContainer>
);

export const CategoryDonutChart = ({ data }: { data: CountPoint[] }) => (
  <ResponsiveContainer width="100%" height={240}>
    <PieChart>
      <Pie
        data={data.map((item) => ({ ...item, key: titleCase(item.key) }))}
        dataKey="count"
        nameKey="key"
        innerRadius={54}
        outerRadius={84}
        paddingAngle={2}
        stroke="none"
      >
        {data.map((entry, index) => (
          <Cell key={entry.key} fill={SERIES_COLORS[index % SERIES_COLORS.length]} />
        ))}
      </Pie>
      <Tooltip {...tooltipStyle} />
      <Legend wrapperStyle={{ fontSize: 11, color: '#8B95A9' }} />
    </PieChart>
  </ResponsiveContainer>
);

export const IncidentTimelineChart = ({ data }: { data: { bucket: string; count: number }[] }) => (
  <ResponsiveContainer width="100%" height={160}>
    <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -24 }}>
      <defs>
        <linearGradient id="incidentFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#FF5C7A" stopOpacity={0.35} />
          <stop offset="100%" stopColor="#FF5C7A" stopOpacity={0} />
        </linearGradient>
      </defs>
      <CartesianGrid stroke={GRID} vertical={false} />
      <XAxis dataKey="bucket" tickFormatter={formatChartLabel} tickLine={false} axisLine={false} {...AXIS} />
      <YAxis allowDecimals={false} tickLine={false} axisLine={false} {...AXIS} />
      <Tooltip {...tooltipStyle} labelFormatter={(value) => formatChartLabel(String(value))} />
      <Area
        type="monotone"
        dataKey="count"
        name="Events"
        stroke="#FF5C7A"
        strokeWidth={1.5}
        fill="url(#incidentFill)"
      />
    </AreaChart>
  </ResponsiveContainer>
);
