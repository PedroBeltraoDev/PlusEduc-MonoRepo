// Hook personalizado para gerenciar estados da API

import { useState, useEffect } from 'react';

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  loadingState: LoadingState;
}

interface UseApiOptions {
  immediate?: boolean;
}

export function useApi<T>(
  apiFunction: () => Promise<T>,
  dependencies: any[] = [],
  options: UseApiOptions = { immediate: true }
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
    loadingState: 'idle'
  });

  const execute = async () => {
    setState(prev => ({
      ...prev,
      loading: true,
      loadingState: 'loading',
      error: null
    }));

    try {
      const result = await apiFunction();
      setState({
        data: result,
        loading: false,
        error: null,
        loadingState: 'success'
      });
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
      setState({
        data: null,
        loading: false,
        error: errorMessage,
        loadingState: 'error'
      });
      throw err;
    }
  };

  const refetch = () => {
    return execute();
  };

  const reset = () => {
    setState({
      data: null,
      loading: false,
      error: null,
      loadingState: 'idle'
    });
  };

  useEffect(() => {
    if (options.immediate) {
      execute();
    }
  }, dependencies);

  return {
    ...state,
    execute,
    refetch,
    reset
  };
}

// Hook específico para listas com busca
export function useApiList<T>(
  fetchFunction: () => Promise<T[]>,
  dependencies: any[] = []
) {
  const {
    data,
    loading,
    error,
    loadingState,
    execute,
    refetch,
    reset
  } = useApi(fetchFunction, dependencies);

  const [searchTerm, setSearchTerm] = useState('');
  const [filteredData, setFilteredData] = useState<T[]>([]);

  // Função genérica de filtro - pode ser sobrescrita
  const filterFunction = (items: T[], term: string): T[] => {
    if (!term) return items;
    return items.filter((item: any) =>
      Object.values(item).some(value =>
        String(value).toLowerCase().includes(term.toLowerCase())
      )
    );
  };

  useEffect(() => {
    if (data) {
      setFilteredData(filterFunction(data, searchTerm));
    } else {
      setFilteredData([]);
    }
  }, [data, searchTerm]);

  return {
    data: filteredData,
    originalData: data,
    loading,
    error,
    loadingState,
    searchTerm,
    setSearchTerm,
    execute,
    refetch,
    reset,
    isEmpty: !loading && filteredData.length === 0,
    total: data?.length || 0,
    filteredTotal: filteredData.length
  };
}