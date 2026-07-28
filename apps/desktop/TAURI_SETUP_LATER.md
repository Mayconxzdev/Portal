# 🖥️ Planejamento de Configuração do Tauri (Desktop Nático)

Este documento registra as diretrizes, pré-requisitos e passos para configurar o **Tauri** no Portal Vesper em fases futuras do Roadmap.

---

## 🧐 Justificativa de Adiamento

O Tauri é um excelente framework para construir aplicações desktop leves usando tecnologias web (React/Vite). Porém, ele introduz requisitos adicionais no ambiente do desenvolvedor, como:
- Ferramentas de compilação C++ (Build Tools do Visual Studio no Windows).
- Compilador **Rust** (`rustc` e `cargo`).
- Configurações complexas de segurança para chamadas locais.

Para evitar que esses pré-requisitos bloqueiem o desenvolvimento ágil da fundação do Portal e de suas regras de negócio centrais, optamos por consolidar a Single Page Application (SPA) na Web primeiro. Como o Tauri simplesmente empacota o build final da SPA (`apps/web/dist/`), iniciá-lo posteriormente será uma integração direta e simples.

---

## 🛠️ Passo a Passo para Inicialização Futura

Quando a equipe decidir habilitar o Tauri, estes serão os passos necessários:

### 1. Pré-requisitos do Sistema (Windows)
1. Instale o Rustup (compilador Rust) de [rustup.rs](https://rustup.rs).
2. Instale o C++ Build Tools através do instalador do Visual Studio.

### 2. Inicializar o Tauri no Monorepo
Navegue para a raiz e execute o CLI do tauri para iniciar o setup:
```bash
npm install -D @tauri-apps/cli
npx tauri init
```

Ao rodar a inicialização, responda as perguntas do assistente:
- **What is your app name?** `portal-vesper`
- **What is the window title?** `Portal Vesper`
- **Where are your web assets located?** `../web/dist` (Aponta para o build de produção do frontend)
- **What is the url of your dev server?** `http://localhost:5173` (Aponta para o Vite em desenvolvimento)
- **What is your frontend dev command?** `npm run dev`
- **What is your frontend build command?** `npm run build`

### 3. Rodar a aplicação em modo Desktop
Após a inicialização básica:
```bash
npx tauri dev
```
O Tauri abrirá uma janela do sistema operacional renderizando o portal com excelente performance nativa e consumo mínimo de memória RAM (ao contrário de soluções baseadas em Electron).
