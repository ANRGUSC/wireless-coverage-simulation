import styles from './Sidebar.module.css';

interface StatsPanelProps {
  bsCount: number;
  coveragePercent: number;
  maxRange: number;
}

export default function StatsPanel({ bsCount, coveragePercent, maxRange }: StatsPanelProps) {
  return (
    <div className={styles.panel}>
      <h3 className={styles.panelTitle}>Coverage Statistics</h3>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Base Stations</span>
        <span className={styles.statValue}>{bsCount}</span>
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Coverage</span>
        <span className={styles.statValue}>{coveragePercent.toFixed(1)}%</span>
      </div>
      <div className={styles.coverageBar}>
        <div className={styles.coverageBarFill} style={{ width: `${Math.min(100, coveragePercent)}%` }} />
      </div>
      <div className={styles.statRow}>
        <span className={styles.statLabel}>Max Range</span>
        <span className={styles.statValue}>{maxRange.toFixed(1)} m</span>
      </div>
    </div>
  );
}
