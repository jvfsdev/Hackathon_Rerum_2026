# Requisitos — Hackathon UFJF 2026

> XXVIII Semana da Computação DCC/UFJF · RERUM Engenharia de Sistemas
> Tema: **Uso de IA na produção de Sistemas Especialistas em benefício da Pecuária Leiteira**
> *(Baseado exclusivamente na apresentação e no documento oficial do evento.)*

---

## 1. Requisito central

Construir uma **aplicação para usuário final** que resolva um problema da pecuária leiteira por meio de uma **base explícita de conhecimento** e um **motor de inferência**.

> ⚠️ **Não use a LLM como o sistema especialista.**
> A IA ajuda a construir (gera, explica, ajuda a extrair regras); **quem decide é a base de conhecimento com o motor de inferência — determinístico e auditável.**

---

## 2. Escolha de tema (obrigatório escolher um)

O tema define o conhecimento a modelar; **a arquitetura é a mesma para os três**.

| Tema | Aplicação esperada |
|---|---|
| **T1 — Anamnese** | Coleta estruturada de sinais e histórico de bovinos leiteiros em lactação, com **triagem explicável**. |
| **T2 — Dietas** | Formulação e verificação de dietas para bovinos leiteiros, de acordo com **raça, peso médio por lote, idade, estado produtivo, destinação econômica, produção, etc**. |
| **T3 — Economia** | Análise econômica e financeira com **dados zootécnicos e custos de insumos**. |

---

## 3. Requisitos de arquitetura

Fluxo esperado:

```
Agente de IA + equipe  →  Base de conhecimento  →  Motor de inferência  →  Aplicação final
(análise, planejamento,   (regras de produção      (encadeamento,          (diálogo com o usuário,
 extração das regras)      explícitas, versionadas)  incerteza, explicação)  resultado explicável)
```

### Componentes do modelo conceitual

- [ ] **Base de conhecimento** — regras, variáveis e pesos (**CF – fatores de certeza**); **versionada e revisada**.
- [ ] **Motor de inferência** — casa regras com fatos, **resolve conflitos** e dispara regras; suporta **encadeamento** e **tratamento de incerteza**.
- [ ] **Memória de trabalho** — fatos da sessão atual (respostas do usuário + conclusões).
- [ ] **Interface do usuário** — exibe perguntas, coleta respostas e apresenta o **parecer final**.
- [ ] **Módulo de explicação** — responde **"por quê?"** e **"como?"** a partir do **traço de inferência** (regras disparadas).
- [ ] **Aquisição de conhecimento** — processo especialista + engenheiro para editar a base.
- [ ] *(Opcional no modelo)* **Fontes de dados externas** — prontuário, sensores, APIs alimentando a memória de trabalho.

---

## 4. Requisitos técnicos

- [ ] Desenvolvimento **obrigatoriamente apoiado por um agente de IA** (ex.: Codex, Claude Code, Copilot, Gemini Code Assist, Opencode).
- [ ] (Opcional, liberado) Uso de **ferramentas e códigos open source** disponíveis na web.
- [ ] Linguagem/tecnologia de **livre escolha** do grupo.
- [ ] A solução final deve **rodar por completo em LOCALHOST**.
- [ ] **Testes com casos conhecidos**: definir casos de teste com resultado esperado (com base no conhecimento do domínio) e **validar cada versão da base**.

---

## 5. Entregáveis obrigatórios

- [ ] **Sistema funcionando** — demonstração ao vivo, rodando em localhost.
- [ ] **Documentação** contendo:
  - [ ] Processo de desenvolvimento (incluindo o uso da IA)
  - [ ] Arquitetura tecnológica
  - [ ] **Regras de produção utilizadas**
- [ ] **Apresentação** mostrando de forma organizada todo o processo, **do uso da IA ao resultado**.
- [ ] **Código-fonte**.

---

## 6. Processo sugerido (diretrizes)

1. Escolher o agente de IA.
2. Pedir à IA para explicar o que é um sistema especialista e como funciona um motor de inferência.
3. Escolher a tecnologia de desenvolvimento.
4. Pesquisar e entender o contexto de negócio do tema, com apoio da IA.
5. Definir claramente o escopo e as diretrizes da arquitetura.
6. Definir as regras de produção.
7. Implementar e testar.
8. Estudar e entender em detalhes o que foi produzido.

---

## 7. Critérios de avaliação

- Nota de **1 a 10**, segundo o **potencial de a solução resolver de fato o problema proposto**.
- **Complexidade** e **grau de assertividade**: critérios de desempate e definem a nota de partida.
- Soluções tratadas como **provas de conceito**; além da completude, avalia-se:
  - capacidade do grupo de **se organizar junto com a IA**;
  - **conhecimento adquirido** no caminho.
- Os integrantes devem demonstrar:
  - habilidade no uso de agentes de codificação com IA;
  - trabalho em equipe;
  - liderança;
  - controle emocional.

---

## 8. Regras gerais e prazos

- Grupos de **1 a 3 participantes** (apenas inscritos e presentes na apresentação).
- **Início:** terça, 20/10, às 9:00.
- **Entrega:** até **20:00 de quinta, 22/10** — enviar documentação, apresentação e código-fonte por e-mail ou WhatsApp, **identificando todos do grupo com nome e telefone**.
  - Suporte/entrega: Carlos Lima — carlos.lima@rerum.com.br · WhatsApp 11 9.8323-9910
- **Demonstração:** sexta, 23/10, às 9:00 (solução rodando em localhost).
- **Resultado:** divulgado na festa de encerramento.
- Premiação por grupo: 1º R$ 1.500 · 2º R$ 900 · 3º R$ 600.
- Opcional: o grupo pode pedir orientação a técnicos da RERUM.
