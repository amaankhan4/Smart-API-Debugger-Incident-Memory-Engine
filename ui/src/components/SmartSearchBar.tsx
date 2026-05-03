import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUiStore } from 'store/useUiStore';

export const SmartSearchBar = () => {
  const navigate = useNavigate();
  const smartSearch = useUiStore((state) => state.smartSearch);
  const setSmartSearch = useUiStore((state) => state.setSmartSearch);
  const [local, setLocal] = useState(smartSearch);

  useEffect(() => setLocal(smartSearch), [smartSearch]);

  return (
    <div className="relative w-full">
      <input
        className="input pl-10"
        placeholder='Semantic search (e.g. "SOAP rate limit error")'
        value={local}
        onChange={(e) => {
          const value = e.target.value;
          setLocal(value);
          setSmartSearch(value);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            navigate('/logs');
          }
        }}
      />
      <span className="pointer-events-none absolute left-3 top-2.5 text-sm text-slate-500">⌘K</span>
    </div>
  );
};
