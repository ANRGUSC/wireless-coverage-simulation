import styles from './Sidebar.module.css';

export default function InstructionsPanel() {
  return (
    <div className={styles.panel}>
      <h3 className={styles.panelTitle}>Instructions</h3>
      <ul className={styles.instructionsList}>
        <li><strong>Left-click</strong> on map to place a base station</li>
        <li><strong>Drag</strong> a base station to move it</li>
        <li><strong>Right-click</strong> a base station to delete it</li>
        <li><strong>Apply Parameters</strong> to recalculate coverage</li>
      </ul>
    </div>
  );
}
