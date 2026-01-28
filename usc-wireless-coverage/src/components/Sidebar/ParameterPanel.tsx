import { useState } from 'react';
import type { CoverageParams } from '../../types/index.ts';
import styles from './Sidebar.module.css';

interface ParameterPanelProps {
  params: CoverageParams;
  onApply: (params: CoverageParams) => void;
  disabled: boolean;
}

interface FieldConfig {
  key: keyof CoverageParams;
  label: string;
  unit: string;
  displayMultiplier?: number;
  min: number;
  max: number;
  step: number;
  tooltip: string;
}

const FIELDS: FieldConfig[] = [
  { key: 'txPower', label: 'TX Power', unit: 'dBm', min: -30, max: 50, step: 1, tooltip: 'Transmit power. Typical: -10 to 30 dBm' },
  { key: 'noise', label: 'Noise Floor', unit: 'dBm', min: -120, max: -60, step: 1, tooltip: 'Noise floor. For 20 MHz bandwidth: ~-101 dBm' },
  { key: 'snrThreshold', label: 'SNR Threshold', unit: 'dB', min: 0, max: 40, step: 1, tooltip: 'Minimum SNR for connectivity. Typical: 10-20 dB' },
  { key: 'shadowStd', label: 'Shadowing Std', unit: 'dB', min: 0, max: 15, step: 0.5, tooltip: 'Shadowing std dev. Typical: 4-8 dB for urban' },
  { key: 'freqHz', label: 'Frequency', unit: 'GHz', displayMultiplier: 1e-9, min: 0.1, max: 100, step: 0.1, tooltip: 'Carrier frequency. Common: 2.4 GHz (WiFi), 3.5 GHz (5G)' },
];

export default function ParameterPanel({ params, onApply, disabled }: ParameterPanelProps) {
  const [localParams, setLocalParams] = useState(params);

  function getDisplayValue(field: FieldConfig): number {
    const raw = localParams[field.key];
    return field.displayMultiplier ? raw * field.displayMultiplier : raw;
  }

  function setDisplayValue(field: FieldConfig, display: number) {
    const raw = field.displayMultiplier ? display / field.displayMultiplier : display;
    setLocalParams(prev => ({ ...prev, [field.key]: raw }));
  }

  function handleApply() {
    onApply(localParams);
  }

  return (
    <div className={styles.panel}>
      <h3 className={styles.panelTitle}>Radio/PHY Parameters</h3>
      {FIELDS.map(field => {
        const displayVal = getDisplayValue(field);
        return (
          <div key={field.key} className={styles.field}>
            <label className={styles.fieldLabel} title={field.tooltip}>
              {field.label} ({field.unit})
            </label>
            <div className={styles.fieldInputRow}>
              <input
                type="range"
                className={styles.slider}
                min={field.min}
                max={field.max}
                step={field.step}
                value={displayVal}
                onChange={e => setDisplayValue(field, parseFloat(e.target.value))}
              />
              <input
                type="number"
                className={styles.numberInput}
                value={displayVal}
                step={field.step}
                onChange={e => {
                  const v = parseFloat(e.target.value);
                  if (!isNaN(v)) setDisplayValue(field, v);
                }}
              />
            </div>
          </div>
        );
      })}
      <button className={styles.applyButton} onClick={handleApply} disabled={disabled}>
        Apply Parameters
      </button>
    </div>
  );
}
