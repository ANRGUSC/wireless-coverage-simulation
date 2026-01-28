import type { CoverageParams } from '../../types/index.ts';
import ParameterPanel from './ParameterPanel.tsx';
import StatsPanel from './StatsPanel.tsx';
import InstructionsPanel from './InstructionsPanel.tsx';
import styles from './Sidebar.module.css';

interface SidebarProps {
  params: CoverageParams;
  onApplyParams: (params: CoverageParams) => void;
  bsCount: number;
  coveragePercent: number;
  maxRange: number;
  isCalculating: boolean;
  progress: { current: number; total: number } | null;
  onClearAll: () => void;
  onExport: () => void;
}

export default function Sidebar({
  params, onApplyParams, bsCount, coveragePercent, maxRange,
  isCalculating, progress, onClearAll, onExport,
}: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.header}>
        <h2 className={styles.title}>USC Wireless Coverage</h2>
        <p className={styles.subtitle}>Interactive Simulator</p>
      </div>

      <ParameterPanel params={params} onApply={onApplyParams} disabled={isCalculating} />
      <StatsPanel bsCount={bsCount} coveragePercent={coveragePercent} maxRange={maxRange} />

      {isCalculating && (
        <div className={styles.progressPanel}>
          <div className={styles.progressText}>
            {progress ? `Calculating BS ${progress.current}/${progress.total}...` : 'Starting calculation...'}
          </div>
          <div className={styles.progressBar}>
            <div
              className={styles.progressBarFill}
              style={{ width: progress ? `${(progress.current / progress.total) * 100}%` : '0%' }}
            />
          </div>
        </div>
      )}

      <InstructionsPanel />

      <div className={styles.actions}>
        <button className={styles.actionButton} onClick={onClearAll} disabled={isCalculating}>
          Clear All Base Stations
        </button>
        <button className={styles.actionButton} onClick={onExport}>
          Export as PNG
        </button>
      </div>

      <div className={styles.footer}>
        <p>Bhaskar Krishnamachari, USC</p>
      </div>
    </aside>
  );
}
