import { useReducer, useEffect, useCallback, useRef, useState } from 'react';
import type { BaseStation, CoverageParams, CoverageResult, BuildingMaskData } from './types/index.ts';
import { loadBuildingMask } from './utils/imageLoader.ts';
import { exportCanvasAsPng } from './utils/exportPng.ts';
import { useCoverageWorker } from './hooks/useCoverageWorker.ts';
import { useDebounce } from './hooks/useDebounce.ts';
import Sidebar from './components/Sidebar/Sidebar.tsx';
import MapCanvas from './components/MapCanvas/MapCanvas.tsx';
import styles from './App.module.css';

interface AppState {
  baseStations: BaseStation[];
  params: CoverageParams;
  nextId: number;
}

type Action =
  | { type: 'ADD_BS'; px: number; py: number }
  | { type: 'MOVE_BS'; id: number; px: number; py: number }
  | { type: 'DELETE_BS'; id: number }
  | { type: 'CLEAR_ALL' }
  | { type: 'SET_PARAMS'; params: CoverageParams };

const DEFAULT_PARAMS: CoverageParams = {
  txPower: -10.0,
  noise: -101.0,
  snrThreshold: 10.0,
  shadowStd: 4.0,
  freqHz: 2.4e9,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'ADD_BS':
      return {
        ...state,
        baseStations: [...state.baseStations, { id: state.nextId, px: action.px, py: action.py }],
        nextId: state.nextId + 1,
      };
    case 'MOVE_BS':
      return {
        ...state,
        baseStations: state.baseStations.map(bs =>
          bs.id === action.id ? { ...bs, px: action.px, py: action.py } : bs
        ),
      };
    case 'DELETE_BS':
      return {
        ...state,
        baseStations: state.baseStations.filter(bs => bs.id !== action.id),
      };
    case 'CLEAR_ALL':
      return { ...state, baseStations: [] };
    case 'SET_PARAMS':
      return { ...state, params: action.params };
    default:
      return state;
  }
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, {
    baseStations: [],
    params: DEFAULT_PARAMS,
    nextId: 1,
  });

  const [maskData, setMaskData] = useState<BuildingMaskData | null>(null);
  const [mapImage, setMapImage] = useState<HTMLImageElement | null>(null);
  const [statusMessage, setStatusMessage] = useState('Loading map...');
  const [coverageResult, setCoverageResult] = useState<CoverageResult | null>(null);

  const { calculate, result, isCalculating, progress, isReady } = useCoverageWorker(maskData);

  // Load building mask on mount
  useEffect(() => {
    loadBuildingMask('/usc_map_buildings_bw.png').then(data => {
      setMaskData({ mask: data.mask, width: data.width, height: data.height, outdoorCount: data.outdoorCount });
      setMapImage(data.rawImage);
      setStatusMessage('Click on the map to place base stations');
    }).catch(err => {
      setStatusMessage(`Error loading map: ${err}`);
    });
  }, []);

  // When worker returns a result, store it
  useEffect(() => {
    if (result) {
      setCoverageResult(result);
      setStatusMessage(`Coverage: ${result.coveragePercent.toFixed(1)}% | Max range: ${result.maxRange.toFixed(1)}m`);
    }
  }, [result]);

  // Debounce base station changes for recalculation
  const bsKey = JSON.stringify(state.baseStations.map(bs => ({ px: bs.px, py: bs.py })));
  const debouncedBsKey = useDebounce(bsKey, 150);
  const debouncedParams = useDebounce(state.params, 150);

  // Trigger calculation when BS or params change
  const prevCalcRef = useRef<string>('');
  useEffect(() => {
    if (!isReady || !maskData) return;
    const key = debouncedBsKey + JSON.stringify(debouncedParams);
    if (key === prevCalcRef.current) return;
    prevCalcRef.current = key;

    const bsPositions = state.baseStations.map(bs => ({ px: bs.px, py: bs.py }));

    if (bsPositions.length === 0) {
      setCoverageResult(null);
      setStatusMessage('Click on the map to place base stations');
      return;
    }

    setStatusMessage('Recalculating coverage...');
    calculate(bsPositions, debouncedParams);
  }, [debouncedBsKey, debouncedParams, isReady, maskData, calculate, state.baseStations]);

  const handleAddBS = useCallback((px: number, py: number) => {
    if (!maskData) return;
    if (maskData.mask[py * maskData.width + px] === 1) {
      setStatusMessage('Cannot place base station inside a building');
      setTimeout(() => setStatusMessage('Click on the map to place base stations'), 2000);
      return;
    }
    dispatch({ type: 'ADD_BS', px, py });
    setStatusMessage(`Added base station ${state.baseStations.length + 1}`);
  }, [maskData, state.baseStations.length]);

  const handleMoveBS = useCallback((id: number, px: number, py: number) => {
    dispatch({ type: 'MOVE_BS', id, px, py });
  }, []);

  const handleDeleteBS = useCallback((id: number) => {
    dispatch({ type: 'DELETE_BS', id });
    setStatusMessage('Deleted base station');
  }, []);

  const handleClearAll = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL' });
    setStatusMessage('Cleared all base stations');
  }, []);

  const handleExport = useCallback(() => {
    const canvas = document.querySelector('canvas');
    if (canvas) {
      exportCanvasAsPng(canvas);
      setStatusMessage('Map exported as PNG');
    }
  }, []);

  const handleApplyParams = useCallback((params: CoverageParams) => {
    dispatch({ type: 'SET_PARAMS', params });
  }, []);

  return (
    <div className={styles.app}>
      <Sidebar
        params={state.params}
        onApplyParams={handleApplyParams}
        bsCount={state.baseStations.length}
        coveragePercent={coverageResult?.coveragePercent ?? 0}
        maxRange={coverageResult?.maxRange ?? 0}
        isCalculating={isCalculating}
        progress={progress}
        onClearAll={handleClearAll}
        onExport={handleExport}
      />
      <MapCanvas
        maskData={maskData}
        mapImage={mapImage}
        baseStations={state.baseStations}
        coverageResult={coverageResult}
        isCalculating={isCalculating}
        onAddBS={handleAddBS}
        onMoveBS={handleMoveBS}
        onDeleteBS={handleDeleteBS}
        statusMessage={statusMessage}
      />
    </div>
  );
}
