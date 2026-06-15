import { useState, useCallback } from 'react';
import Map from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { MAPBOX_TOKEN } from '../../constants';
import DemandHeatmap from './DemandHeatmap';
import ZoneChoropleth from './ZoneChoropleth';
import StagingPins from './StagingPins';
import ZoneTooltip from './ZoneTooltip';
import StationLayer, { StationTooltip } from './StationLayer';
import EquityLayer from './EquityLayer';

const INITIAL_VIEW = {
  longitude: -73.97,
  latitude: 40.73,
  zoom: 10.5,
  pitch: 0,
  bearing: 0,
};

export default function MapContainer({ heatmapData, stagingData, layerVisibility, selectedZone, onZoneClick, ambulanceCount, counterfactualByZone, overlays = {} }) {
  const [hoverInfo, setHoverInfo] = useState(null);
  const [stationHover, setStationHover] = useState(null);

  const interactiveLayerIds = [
    ...(layerVisibility.heatmap ? ['zone-fill', 'zip-fill'] : []),
    ...(layerVisibility.stations ? ['ems-stations-circle'] : []),
  ];

  const onMouseMove = useCallback((e) => {
    const feature = e.features && e.features[0];
    if (!feature) {
      setHoverInfo(null);
      setStationHover(null);
      return;
    }
    if (feature.layer?.id === 'ems-stations-circle') {
      setStationHover({ x: e.point.x, y: e.point.y, properties: feature.properties });
      setHoverInfo(null);
    } else {
      setHoverInfo({ x: e.point.x, y: e.point.y, properties: feature.properties });
      setStationHover(null);
    }
  }, []);

  const onMouseLeave = useCallback(() => {
    setHoverInfo(null);
    setStationHover(null);
  }, []);

  const onClick = useCallback((e) => {
    const feature = e.features && e.features[0];
    if (feature && feature.properties?.zone) {
      onZoneClick(feature.properties.zone);
    }
  }, [onZoneClick]);

  return (
    <div style={{ flex: 1, position: 'relative' }}>
        <Map
          initialViewState={INITIAL_VIEW}
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          interactiveLayerIds={interactiveLayerIds}
          onMouseMove={onMouseMove}
          onMouseLeave={onMouseLeave}
          onClick={onClick}
          style={{ width: '100%', height: '100%' }}
        >
          <DemandHeatmap heatmapData={heatmapData} visible={layerVisibility.heatmap} />
          {layerVisibility.heatmap && <ZoneChoropleth data={heatmapData} />}
          <StagingPins
            data={stagingData}
            showPins={layerVisibility.staging}
            showCoverage={layerVisibility.coverage}
            ambulanceCount={ambulanceCount}
            counterfactualByZone={counterfactualByZone}
          />
          <StationLayer visible={layerVisibility.stations} />
          <EquityLayer visible={overlays.equity} />
        </Map>
        {hoverInfo && <ZoneTooltip info={hoverInfo} />}
        {stationHover && <StationTooltip info={stationHover} />}
    </div>
  );
}
