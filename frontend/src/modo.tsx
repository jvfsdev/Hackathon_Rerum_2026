import { createContext, useContext } from 'react'
import type { Modo } from './api'

/** Visão da interface: "produtor" (linguagem de fazenda) ou "tecnico" (regras, CF, traço). */
export const ModoContexto = createContext<{ modo: Modo; setModo: (m: Modo) => void }>({ modo: 'produtor', setModo: () => {} })
export const useModo = () => useContext(ModoContexto)
