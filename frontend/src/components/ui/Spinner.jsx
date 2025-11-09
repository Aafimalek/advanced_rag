import React from 'react';

const Spinner = () => (
  <div className="inline-flex items-center justify-center">
    <div className="relative w-5 h-5">
      <div className="absolute inset-0 border-2 border-orange-500/20 rounded-full"></div>
      <div className="absolute inset-0 border-2 border-transparent border-t-orange-500 border-r-amber-500 rounded-full animate-spin"></div>
    </div>
  </div>
);

export default Spinner;
