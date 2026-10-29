import { describe, expect, it } from 'vitest'
import { dataCurta, duracao, esporte, hora, km, ritmo, variacao, velocidadeParaRitmo } from './formato'

describe('formato', () => {
  it('ritmo em m:ss/km', () => {
    expect(ritmo(298)).toBe('4:58/km')
    expect(ritmo(330.4)).toBe('5:30/km')
    expect(ritmo(359.6)).toBe('6:00/km')
    expect(ritmo(null)).toBe('-')
  })

  it('velocidade vira ritmo e parado vira null', () => {
    expect(velocidadeParaRitmo(3.333)).toBeCloseTo(300, 0)
    expect(velocidadeParaRitmo(0.2)).toBeNull()
    expect(velocidadeParaRitmo(null)).toBeNull()
  })

  it('duração', () => {
    expect(duracao(48.4)).toBe('48 min')
    expect(duracao(65)).toBe('1h05')
    expect(duracao(undefined)).toBe('-')
  })

  it('distância e variação em pt-BR', () => {
    expect(km(10.034)).toBe('10,03 km')
    expect(km(null)).toBe('-')
    expect(variacao(1.25)).toBe('+1,3')
    expect(variacao(-3)).toBe('-3,0')
  })

  it('datas no fuso que vem da API', () => {
    expect(dataCurta('2026-10-20T07:52-03:00')).toBe('ter, 20/10')
    expect(dataCurta('2026-10-26', false)).toBe('26/10')
    expect(hora('2026-10-20T07:52-03:00')).toBe('07:52')
  })

  it('nomes dos esportes', () => {
    expect(esporte('run')).toBe('Corrida')
    expect(esporte('desconhecido')).toBe('desconhecido')
  })
})
