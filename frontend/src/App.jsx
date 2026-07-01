import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import { Navigation, Loader2, Route, Plus, X } from 'lucide-react';
import AutocompleteInput from './AutocompleteInput';
import './index.css';

// Component to dynamically fit the bounds of the map to the routes
const MapBounds = ({ markers }) => {
  const map = useMap();
  useEffect(() => {
    if (markers && markers.length > 0) {
      const bounds = markers.map(m => [m.lat, m.lon]);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [markers, map]);
  return null;
};

function App() {
  const [start, setStart] = useState('Gateway of India, Mumbai');
  const [stops, setStops] = useState(['Chhatrapati Shivaji Terminus, Mumbai', 'Marine Drive, Mumbai']);
  const [end, setEnd] = useState('Bandra Kurla Complex, Mumbai');
  const [timeOfDay, setTimeOfDay] = useState('Morning Rush (8 AM)');
  const [weather, setWeather] = useState('Clear');
  
  const [loading, setLoading] = useState(false);
  const [routeData, setRouteData] = useState(null);
  const [error, setError] = useState(null);

  const handleOptimize = async () => {
    setLoading(true);
    setError(null);
    setRouteData(null);
    
    try {
      const stopsArray = stops.filter(s => s.trim());
      
      const response = await fetch('http://localhost:8000/api/optimize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          start,
          stops: stopsArray,
          end,
          time_of_day: timeOfDay,
          weather,
        }),
      });
      
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Optimization failed');
      }
      
      const data = await response.json();
      setRouteData(data);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Overlay */}
      <div className="sidebar glass-panel">
        <div className="sidebar-header">
          <h1 className="gradient-text">NeuroNav</h1>
          <p>Smartest sequence, minimum traffic.</p>
        </div>
        
        <div className="input-group">
          <label>Start Location</label>
          <AutocompleteInput value={start} onChange={setStart} placeholder="Search start location..." />
        </div>
        
        <div className="input-group">
          <label>Intermediate Stops</label>
          <div className="stops-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {stops.map((stop, index) => (
              <div key={index} style={{ display: 'flex', gap: '8px' }}>
                <div style={{ flex: 1 }}>
                  <AutocompleteInput 
                    value={stop} 
                    onChange={(val) => {
                      const newStops = [...stops];
                      newStops[index] = val;
                      setStops(newStops);
                    }} 
                    placeholder={`Stop ${index + 1}`} 
                  />
                </div>
                <button 
                  className="btn-icon" 
                  onClick={() => {
                    const newStops = stops.filter((_, i) => i !== index);
                    setStops(newStops);
                  }}
                  title="Remove Stop"
                >
                  <X size={18} />
                </button>
              </div>
            ))}
          </div>
          <button 
            className="btn-secondary" 
            onClick={() => setStops([...stops, ''])}
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '4px' }}
          >
            <Plus size={16} /> Add Stop
          </button>
        </div>
        
        <div className="input-group">
          <label>End Location</label>
          <AutocompleteInput value={end} onChange={setEnd} placeholder="Search end location..." />
        </div>
        
        <div className="input-group">
          <label>Time of Day</label>
          <select value={timeOfDay} onChange={e => setTimeOfDay(e.target.value)}>
            <option>Morning Rush (8 AM)</option>
            <option>Midday (1 PM)</option>
            <option>Evening Rush (6 PM)</option>
            <option>Night (11 PM)</option>
          </select>
        </div>
        
        <div className="input-group">
          <label>Weather Conditions</label>
          <select value={weather} onChange={e => setWeather(e.target.value)}>
            <option>Clear</option>
            <option>Rain</option>
            <option>Storm</option>
          </select>
        </div>
        
        <button className="btn-primary" onClick={handleOptimize} disabled={loading}>
          {loading ? <Loader2 size={20} className="animate-spin" /> : <Route size={20} />}
          {loading ? 'Optimizing...' : 'Calculate Optimal Route'}
        </button>
        
        {error && <div style={{ color: '#ef4444', fontSize: '0.9rem', marginTop: '10px' }}>{error}</div>}
        
        {routeData && (
          <div className="metrics-container">
            <h3 className="metrics-title">Performance Comparison</h3>
            <div className="metrics-grid">
              <div className="metric-card">
                <span className="metric-label">Naive Route (Distance)</span>
                <span className="metric-value">{routeData.metrics.static_time_mins}m</span>
              </div>
              <div className="metric-card">
                <span className="metric-label">AI Route (Traffic)</span>
                <span className="metric-value">{routeData.metrics.ai_time_mins}m</span>
              </div>
              <div className="metric-card highlight">
                <div>
                  <span className="metric-label" style={{color: 'rgba(255,255,255,0.7)'}}>Time Saved by AI</span>
                  <div className="metric-value">{routeData.metrics.saved_time_mins}m</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Map Area */}
      <div className="map-container">
        {loading && (
          <div className="loader-overlay">
            <div className="spinner"></div>
            <div className="loader-text">Analyzing road networks and traffic...</div>
          </div>
        )}
        
        <MapContainer 
          center={[18.9220, 72.8347]} // Default to Mumbai roughly
          zoom={12} 
          zoomControl={false}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          
          {routeData && <MapBounds markers={routeData.markers} />}
          
          {routeData && routeData.traffic_heatmap.map((edge, i) => {
            const isHeavy = edge.level > 0.6;
            const color = isHeavy ? "#ef4444" : "#f97316";
            return (
              <Polyline key={`traffic-${i}`} positions={edge.coords} color={color} weight={3} opacity={0.5} />
            )
          })}
          
          {routeData && routeData.static_route_coords.length > 0 && (
            <Polyline 
              positions={routeData.static_route_coords} 
              color="rgba(255, 255, 255, 0.4)" 
              weight={4} 
              dashArray="8 8"
            />
          )}
          
          {routeData && routeData.ai_route_coords.length > 0 && (
            <Polyline 
              positions={routeData.ai_route_coords} 
              color="#3b82f6" 
              weight={6} 
              opacity={0.9}
            />
          )}
          
          {routeData && routeData.markers.map((m, i) => (
            <Marker key={i} position={[m.lat, m.lon]}>
              <Popup>
                {i === 0 ? "Start" : i === routeData.markers.length - 1 ? "End" : `Stop ${i}`}: {m.address}
              </Popup>
            </Marker>
          ))}
          
        </MapContainer>
      </div>
    </div>
  );
}

export default App;
