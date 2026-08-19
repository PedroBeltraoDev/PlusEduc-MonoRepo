export function Logo({ className = "" }: { className?: string }) {
  return (
    <div className={`flex flex-col items-center ${className}`}>
      <svg width="80" height="80" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Órbitas azuis */}
        <circle cx="60" cy="60" r="55" stroke="#4FC3F7" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.4" fill="none"/>
        <circle cx="60" cy="60" r="45" stroke="#1E5AA8" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.3" fill="none"/>
        
        {/* Engrenagem externa */}
        <path d="M60 15 L62 20 L67 18 L65 23 L70 23 L67 28 L70 33 L65 33 L67 38 L62 36 L60 41 L58 36 L53 38 L55 33 L50 33 L53 28 L50 23 L55 23 L53 18 L58 20 Z" fill="#0A2463" opacity="0.2"/>
        <path d="M15 60 L20 62 L18 67 L23 65 L23 70 L28 67 L33 70 L33 65 L38 67 L36 62 L41 60 L36 58 L38 53 L33 55 L33 50 L28 53 L23 50 L23 55 L18 53 L20 58 Z" fill="#0A2463" opacity="0.2"/>
        <path d="M60 105 L58 100 L53 102 L55 97 L50 97 L53 92 L50 87 L55 87 L53 82 L58 84 L60 79 L62 84 L67 82 L65 87 L70 87 L67 92 L70 97 L65 97 L67 102 L62 100 Z" fill="#0A2463" opacity="0.2"/>
        <path d="M105 60 L100 58 L102 53 L97 55 L97 50 L92 53 L87 50 L87 55 L82 53 L84 58 L79 60 L84 62 L82 67 L87 65 L87 70 L92 67 L97 70 L97 65 L102 67 L100 62 Z" fill="#0A2463" opacity="0.2"/>
        
        {/* Engrenagem central - mais definida */}
        <circle cx="60" cy="60" r="38" fill="#1E5AA8"/>
        
        {/* Dentes da engrenagem */}
        <rect x="57" y="20" width="6" height="8" fill="#1E5AA8" rx="1"/>
        <rect x="57" y="92" width="6" height="8" fill="#1E5AA8" rx="1"/>
        <rect x="20" y="57" width="8" height="6" fill="#1E5AA8" rx="1"/>
        <rect x="92" y="57" width="8" height="6" fill="#1E5AA8" rx="1"/>
        <rect x="30" y="30" width="7" height="7" fill="#1E5AA8" rx="1" transform="rotate(45 33.5 33.5)"/>
        <rect x="83" y="30" width="7" height="7" fill="#1E5AA8" rx="1" transform="rotate(-45 86.5 33.5)"/>
        <rect x="30" y="83" width="7" height="7" fill="#1E5AA8" rx="1" transform="rotate(-45 33.5 86.5)"/>
        <rect x="83" y="83" width="7" height="7" fill="#1E5AA8" rx="1" transform="rotate(45 86.5 86.5)"/>
        
        {/* Fundo branco do livro */}
        <ellipse cx="60" cy="60" rx="28" ry="28" fill="white"/>
        
        {/* Livro aberto */}
        <path d="M60 45 L60 75 M60 45 L45 48 L45 78 L60 75 M60 45 L75 48 L75 78 L60 75" 
              stroke="#0A2463" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        
        {/* Páginas do livro */}
        <path d="M50 52 L50 72 M54 53 L54 73" stroke="#1E5AA8" strokeWidth="1" opacity="0.4"/>
        <path d="M70 52 L70 72 M66 53 L66 73" stroke="#1E5AA8" strokeWidth="1" opacity="0.4"/>
        
        {/* Centro da engrenagem */}
        <circle cx="60" cy="60" r="5" fill="#0A2463"/>
      </svg>
      <div className="text-center mt-2">
        <h1 className="text-2xl font-bold text-[#0A2463]">PlusEduc</h1>
        <p className="text-xs text-gray-500 mt-1">Soluções Inteligentes para a Educação</p>
      </div>
    </div>
  );
}

export function LogoIcon({ className = "" }: { className?: string }) {
  return (
    <svg width="40" height="40" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <circle cx="60" cy="60" r="55" stroke="white" strokeWidth="2" strokeDasharray="4 4" opacity="0.2" fill="none"/>
      <circle cx="60" cy="60" r="38" fill="white" opacity="0.9"/>
      <rect x="57" y="20" width="6" height="8" fill="white" opacity="0.9" rx="1"/>
      <rect x="57" y="92" width="6" height="8" fill="white" opacity="0.9" rx="1"/>
      <rect x="20" y="57" width="8" height="6" fill="white" opacity="0.9" rx="1"/>
      <rect x="92" y="57" width="8" height="6" fill="white" opacity="0.9" rx="1"/>
      <ellipse cx="60" cy="60" rx="28" ry="28" fill="#0A2463"/>
      <path d="M60 45 L60 75 M60 45 L45 48 L45 78 L60 75 M60 45 L75 48 L75 78 L60 75" 
            stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M50 52 L50 72 M54 53 L54 73" stroke="white" strokeWidth="1" opacity="0.3"/>
      <path d="M70 52 L70 72 M66 53 L66 73" stroke="white" strokeWidth="1" opacity="0.3"/>
      <circle cx="60" cy="60" r="5" fill="white"/>
    </svg>
  );
}
