import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface Empresa {
  id: number;
  nome_empresa: string;
  email_admin: string;
  plataforma_ecommerce?: string;
  erp?: string;
  crm?: string;
}

interface EmpresaContextType {
  empresa: Empresa | null;
  setEmpresa: (empresa: Empresa | null) => void;
}

const EmpresaContext = createContext<EmpresaContextType>({
  empresa: null,
  setEmpresa: () => {},
});

export function EmpresaProvider({ children }: { children: ReactNode }) {
  const [empresa, setEmpresaState] = useState<Empresa | null>(() => {
    try {
      const saved = localStorage.getItem('moodlab-empresa');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const setEmpresa = (emp: Empresa | null) => {
    setEmpresaState(emp);
    if (emp) {
      localStorage.setItem('moodlab-empresa', JSON.stringify(emp));
    } else {
      localStorage.removeItem('moodlab-empresa');
    }
  };

  return (
    <EmpresaContext.Provider value={{ empresa, setEmpresa }}>
      {children}
    </EmpresaContext.Provider>
  );
}

export const useEmpresa = () => useContext(EmpresaContext);