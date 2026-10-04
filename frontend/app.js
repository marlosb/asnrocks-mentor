/**
 * Frontend do Mentor: chat com streaming via SSE.
 * JavaScript puro (ES2022), sem dependências externas.
 */

const chatForm = document.getElementById("chat-form");
const campoMensagem = document.getElementById("mensagem");
const listaMensagens = document.getElementById("mensagens");
const seletorModelo = document.getElementById("modelo-select");

/** Bolha do agente em construção durante o streaming da resposta atual. */
let bolhaResposta = null;
/** Texto markdown acumulado da resposta em construção (os deltas chegam em partes). */
let textoRespostaAtual = "";
/** Contagem de chamadas a skills/tools no turno atual, por nome. */
let contadorFerramentas = {};

/** Rótulos amigáveis para as skills/tools mais comuns; nomes desconhecidos usam o bruto. */
const ROTULOS_FERRAMENTAS = {
  skill: "Skill",
  web_search: "Busca na web",
  web_fetch: "Leitura de página",
  bash: "Bash",
  run_python: "Execução de código",
  search_docs: "Busca no acervo",
};

/** Converte um nome de tool desconhecido em um rótulo legível. */
function rotuloFerramenta(nome) {
  if (ROTULOS_FERRAMENTAS[nome]) return ROTULOS_FERRAMENTAS[nome];
  const texto = nome.replace(/[_-]+/g, " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** Registra uma chamada de skill/tool no contador do turno atual. */
function registrarUsoFerramenta(nome) {
  contadorFerramentas[nome] = (contadorFerramentas[nome] ?? 0) + 1;
}

/** Acrescenta à bolha o resumo de skills/tools usadas no turno, se houver algum uso. */
function renderizarResumoFerramentas(container, contador) {
  const nomes = Object.keys(contador);
  if (nomes.length === 0) return;

  const lista = document.createElement("ul");
  lista.className = "resumo-ferramentas";
  for (const nome of nomes) {
    const quantidade = contador[nome];
    const item = document.createElement("li");
    const sufixo = quantidade === 1 ? "chamada" : "chamadas";
    item.textContent = `${rotuloFerramenta(nome)}: ${quantidade} ${sufixo}`;
    lista.appendChild(item);
  }
  container.appendChild(lista);
}

const PADRAO_INLINE = /`([^`]+)`|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_]+)_/g;
const PADRAO_ITEM_LISTA = /^\s*([-*]|\d+\.)\s+/;
const PADRAO_CABECALHO = /^(#{1,6})\s+(.*)/;

/**
 * Renderiza negrito/itálico/código inline dentro de um elemento, criando nós
 * DOM diretamente (sem innerHTML) — conteúdo do agente é dado não confiável.
 */
function renderizarInline(container, texto) {
  PADRAO_INLINE.lastIndex = 0;
  let ultimoIndice = 0;
  let resultado;
  while ((resultado = PADRAO_INLINE.exec(texto)) !== null) {
    if (resultado.index > ultimoIndice) {
      container.appendChild(document.createTextNode(texto.slice(ultimoIndice, resultado.index)));
    }
    const [, codigo, negrito1, negrito2, italico1, italico2] = resultado;
    let elemento;
    if (codigo !== undefined) {
      elemento = document.createElement("code");
      elemento.textContent = codigo;
    } else if (negrito1 !== undefined || negrito2 !== undefined) {
      elemento = document.createElement("strong");
      elemento.textContent = negrito1 ?? negrito2;
    } else {
      elemento = document.createElement("em");
      elemento.textContent = italico1 ?? italico2;
    }
    container.appendChild(elemento);
    ultimoIndice = PADRAO_INLINE.lastIndex;
  }
  if (ultimoIndice < texto.length) {
    container.appendChild(document.createTextNode(texto.slice(ultimoIndice)));
  }
}

/** Dentro de um parágrafo, uma quebra de linha simples vira `<br>`. */
function renderizarParagrafo(container, texto) {
  const linhas = texto.split("\n");
  linhas.forEach((linha, indice) => {
    renderizarInline(container, linha);
    if (indice < linhas.length - 1) {
      container.appendChild(document.createElement("br"));
    }
  });
}

/**
 * Converte um subconjunto simples de markdown (parágrafos, cabeçalhos, listas,
 * blocos de código, negrito/itálico/código inline) em nós DOM. Não usa
 * innerHTML em nenhum momento.
 */
function renderizarMarkdown(container, texto) {
  container.textContent = "";
  const linhas = texto.split("\n");
  let i = 0;
  while (i < linhas.length) {
    const linha = linhas[i];

    if (linha.trim() === "") {
      i++;
      continue;
    }

    if (linha.trim().startsWith("```")) {
      i++;
      const codigoLinhas = [];
      while (i < linhas.length && !linhas[i].trim().startsWith("```")) {
        codigoLinhas.push(linhas[i]);
        i++;
      }
      i++; // pula a cerca de fechamento
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = codigoLinhas.join("\n");
      pre.appendChild(code);
      container.appendChild(pre);
      continue;
    }

    const cabecalho = linha.match(PADRAO_CABECALHO);
    if (cabecalho) {
      const nivel = Math.min(cabecalho[1].length + 2, 6);
      const elemento = document.createElement(`h${nivel}`);
      renderizarInline(elemento, cabecalho[2]);
      container.appendChild(elemento);
      i++;
      continue;
    }

    if (PADRAO_ITEM_LISTA.test(linha)) {
      const ordenada = /^\s*\d+\./.test(linha);
      const lista = document.createElement(ordenada ? "ol" : "ul");
      while (i < linhas.length && PADRAO_ITEM_LISTA.test(linhas[i])) {
        const item = document.createElement("li");
        renderizarInline(item, linhas[i].replace(PADRAO_ITEM_LISTA, ""));
        lista.appendChild(item);
        i++;
      }
      container.appendChild(lista);
      continue;
    }

    const paragrafoLinhas = [];
    while (
      i < linhas.length &&
      linhas[i].trim() !== "" &&
      !linhas[i].trim().startsWith("```") &&
      !PADRAO_ITEM_LISTA.test(linhas[i]) &&
      !PADRAO_CABECALHO.test(linhas[i])
    ) {
      paragrafoLinhas.push(linhas[i]);
      i++;
    }
    const paragrafo = document.createElement("p");
    renderizarParagrafo(paragrafo, paragrafoLinhas.join("\n"));
    container.appendChild(paragrafo);
  }
}

function criarBolha(remetente) {
  const bolha = document.createElement("div");
  bolha.className = `bolha bolha--${remetente}`;
  listaMensagens.appendChild(bolha);
  listaMensagens.scrollTop = listaMensagens.scrollHeight;
  return bolha;
}

function tratarEvento(evento) {
  switch (evento.tipo) {
    case "assistant.message_delta": {
      if (!bolhaResposta) {
        bolhaResposta = criarBolha("agente");
        textoRespostaAtual = "";
        contadorFerramentas = {};
      }
      textoRespostaAtual += evento.dados?.deltaContent ?? "";
      renderizarMarkdown(bolhaResposta, textoRespostaAtual);
      listaMensagens.scrollTop = listaMensagens.scrollHeight;
      break;
    }
    case "assistant.message": {
      if (!bolhaResposta) {
        bolhaResposta = criarBolha("agente");
        contadorFerramentas = {};
      }
      textoRespostaAtual = evento.dados?.content ?? "";
      renderizarMarkdown(bolhaResposta, textoRespostaAtual);
      break;
    }
    case "skill.invoked": {
      registrarUsoFerramenta("skill");
      break;
    }
    case "tool.execution_start": {
      const nomeFerramenta = evento.dados?.toolName;
      if (nomeFerramenta && nomeFerramenta !== "skill") {
        registrarUsoFerramenta(nomeFerramenta);
      }
      break;
    }
    case "session.idle": {
      if (bolhaResposta) {
        renderizarResumoFerramentas(bolhaResposta, contadorFerramentas);
        listaMensagens.scrollTop = listaMensagens.scrollHeight;
      }
      bolhaResposta = null;
      textoRespostaAtual = "";
      contadorFerramentas = {};
      break;
    }
    case "session.error": {
      bolhaResposta = null;
      const erro = criarBolha("sistema");
      const dados = evento.dados ?? {};
      const partes = [dados.message ?? "falha desconhecida"];
      if (dados.statusCode) partes.push(`status ${dados.statusCode}`);
      if (dados.errorCode) partes.push(`código ${dados.errorCode}`);
      if (dados.url) partes.push(dados.url);
      erro.textContent = `Erro no agente: ${partes.join(" — ")}`;
      break;
    }
    default:
      break;
  }
}

function conectarEventos() {
  const fonte = new EventSource("/events");
  fonte.onmessage = (mensagem) => {
    tratarEvento(JSON.parse(mensagem.data));
  };
}

/** Busca os modelos configurados no backend e preenche o seletor. */
async function carregarModelos() {
  const resposta = await fetch("/modelos");
  if (!resposta.ok) return;
  const { modelos, atual } = await resposta.json();

  seletorModelo.textContent = "";
  for (const modelo of modelos) {
    const opcao = document.createElement("option");
    opcao.value = modelo;
    opcao.textContent = modelo;
    opcao.selected = modelo === atual;
    seletorModelo.appendChild(opcao);
  }
  seletorModelo.disabled = modelos.length <= 1;
}

/** Encerra a sessão atual e inicia uma nova com o modelo escolhido. */
async function trocarModelo(modelo) {
  seletorModelo.disabled = true;
  const resposta = await fetch("/modelo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ modelo }),
  });
  const corpo = await resposta.json();

  const aviso = criarBolha("sistema");
  aviso.textContent = resposta.ok
    ? `Modelo trocado para ${corpo.modelo}. Uma nova conversa foi iniciada com esse modelo.`
    : `Não foi possível trocar de modelo: ${corpo.erro ?? "falha desconhecida"}`;

  bolhaResposta = null;
  textoRespostaAtual = "";
  seletorModelo.disabled = false;
}

seletorModelo.addEventListener("change", () => {
  trocarModelo(seletorModelo.value);
});

async function enviarMensagem(texto) {
  const bolha = criarBolha("aluno");
  bolha.textContent = texto;

  const resposta = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensagem: texto }),
  });

  if (!resposta.ok) {
    const erro = criarBolha("sistema");
    erro.textContent = "Não foi possível enviar a mensagem ao Mentor.";
  }
}

chatForm.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const texto = campoMensagem.value.trim();
  if (!texto) return;
  campoMensagem.value = "";
  enviarMensagem(texto);
});

conectarEventos();
carregarModelos();
