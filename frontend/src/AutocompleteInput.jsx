import React, { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';

const AutocompleteInput = ({ value, onChange, placeholder }) => {
  const [query, setQuery] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapperRef = useRef(null);
  const isSelectedRef = useRef(false);
  
  useEffect(() => {
    if (value !== undefined && value !== query) {
      setQuery(value || '');
    }
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [wrapperRef]);

  useEffect(() => {
    if (!query) {
      setSuggestions([]);
      return;
    }
    
    if (isSelectedRef.current) {
      isSelectedRef.current = false;
      return;
    }
    
    const timeoutId = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await fetch(`http://localhost:8000/api/search?q=${encodeURIComponent(query)}`);
        if (response.ok) {
          const data = await response.json();
          setSuggestions(data);
          setShowDropdown(true);
        }
      } catch (error) {
        console.error("Failed to fetch suggestions", error);
      } finally {
        setLoading(false);
      }
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [query]);

  const handleSelect = (suggestion) => {
    isSelectedRef.current = true;
    setQuery(suggestion.display_name);
    onChange(suggestion.display_name);
    setShowDropdown(false);
  };

  return (
    <div className="autocomplete-wrapper" ref={wrapperRef} style={{ position: 'relative', zIndex: showDropdown ? 100 : 1 }}>
      <div style={{ position: 'relative' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            onChange(e.target.value);
          }}
          onFocus={() => {
            if (suggestions.length > 0) setShowDropdown(true);
          }}
          placeholder={placeholder}
          style={{ width: '100%', paddingRight: '30px' }}
        />
        {loading && <Search size={16} className="animate-spin" style={{ position: 'absolute', right: '12px', top: '14px', color: '#9ca3af' }} />}
      </div>
      
      {showDropdown && suggestions.length > 0 && (
        <ul className="autocomplete-dropdown glass-panel">
          {suggestions.map((suggestion, index) => (
            <li 
              key={index} 
              onClick={() => handleSelect(suggestion)}
              className="autocomplete-item"
            >
              {suggestion.display_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default AutocompleteInput;
