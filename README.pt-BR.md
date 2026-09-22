# Key Remap para o Omarchy

Remapeia teclas e atalhos no [Omarchy](https://omarchy.org) — para o sistema inteiro ou só
dentro de um aplicativo. É o que o
[PowerToys Keyboard Manager](https://learn.microsoft.com/windows/powertoys/keyboard-manager)
faz, construído sobre o [keyd](https://github.com/rvaiya/keyd), com a parte "por aplicativo"
ligada direto no Hyprland.

*[Read in English](README.md)*

```bash
omarchy-key-remap add capslock esc                # o clássico
omarchy-key-remap add ctrl+w noop --app chromium  # parar de fechar a aba sem querer
omarchy-key-remap                                 # ou simplesmente abrir o menu
```

## Por que keyd, e por que isto em cima

O keyd remapeia na camada de entrada do kernel, que é o único lugar no Linux onde o remap vale
*em todo lugar*: Wayland, X11, TTY, tela de bloqueio, jogos. O que falta nele é uma porta de
entrada para quem não quer aprender o arquivo de configuração — e, no Hyprland, suporte a
remap por aplicativo (o mapeador do próprio keyd só fala X11 e GNOME).

Isto preenche as duas lacunas:

- **Um menu e uma CLI** no lugar do `/etc/keyd/default.conf`. Seus remaps ficam em
  `~/.config/omarchy-key-remap/remaps.json` e a configuração do keyd é gerada a partir deles.
- **Remap por aplicativo no Hyprland.** Um observador acompanha os eventos de foco do próprio
  compositor e entrega ao keyd os atalhos da janela em que você está — e, tão importante
  quanto, os retira quando você sai dela.
- **Nada é escrito sem o keyd aprovar.** Toda configuração gerada passa pelo `keyd check`
  antes de ser instalada, e um `default.conf` que não tenha sido escrito por esta ferramenta é
  copiado para um backup antes de ser substituído.

## O que dá para remapear

| | Exemplo |
|---|---|
| Uma tecla | `omarchy-key-remap add capslock esc` |
| Um atalho | `omarchy-key-remap add ctrl+shift+c C-insert` |
| Tecla para combinação | `omarchy-key-remap add f13 M-v` |
| Tecla para sequência | `omarchy-key-remap add f5 'macro(C-s C-r)'` |
| Tecla para comando | `omarchy-key-remap add f12 'command(omarchy-menu)'` |
| Nada (desativar) | `omarchy-key-remap add ctrl+w noop --app chromium` |
| Segurar vs tocar | `omarchy-key-remap add capslock 'overload(control, esc)'` |

Os modificadores podem ser escritos como você os chama — `ctrl`, `super`, `win`, `cmd`,
`option` — e são normalizados para os nomes do keyd. O lado direito é a linguagem de ações do
keyd: uma tecla, uma combinação (`C-c`, `M-S-v`) ou uma de `macro()`, `command()`, `layer()`,
`oneshot()`, `overload()`, `toggle()`, `noop`. O `man keyd` tem a lista completa.

## Instalação

### Arch / Omarchy

```bash
sudo pacman -U omarchy-key-remap-*-any.pkg.tar.zst   # dos Releases
omarchy-key-remap setup
```

O `setup` habilita o serviço do keyd e adiciona você ao grupo `keyd` (necessário para os
remaps por aplicativo — precisa sair e entrar na sessão uma vez). Depois:

```bash
omarchy-key-remap add capslock esc
systemctl --user enable --now omarchy-key-remap-apps.service   # só para remap por app
```

### Em outras distros

`pipx install git+https://github.com/andrebbruno/omarchy-key-remap`, com o keyd instalado e
rodando. Tudo funciona em qualquer compositor, menos o observador por aplicativo, que depende
do socket de eventos do Hyprland.

## Comandos

```
omarchy-key-remap                        o menu
omarchy-key-remap add <tecla> <ação>     adiciona um remap e aplica
omarchy-key-remap remove <tecla>         remove um
omarchy-key-remap list                   o que está remapeado
omarchy-key-remap status                 keyd, a configuração, o observador
omarchy-key-remap clear                  desliga tudo, mas guarda para depois
omarchy-key-remap apply                  grava e recarrega (depois de editar o JSON à mão)
omarchy-key-remap capture                imprime a próxima tecla que você apertar
omarchy-key-remap keys [filtro]          todos os nomes de tecla que o keyd aceita
```

`--app <classe>` restringe qualquer um deles a uma classe de janela — a coluna `class` do
`hyprctl clients`. `--note "motivo"` guarda um lembrete junto ao remap.

Um atalho para o menu, se quiser, no `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + ALT + K", "Key remap", "omarchy-key-remap")
```

## ⚠️ Antes de remapear algo importante

- **Um remap ruim pode trancar você fora do próprio teclado.** A saída de emergência do keyd é
  segurar **backspace + escape + enter** juntos: o keyd encerra e o teclado volta ao normal.
  Essa linha também fica no topo de toda configuração gerada por esta ferramenta.
- **Remapear um modificador, ou uma tecla que você precisa para digitar a senha**, vale também
  na tela de bloqueio e no TTY — é o preço de remapear na camada do kernel, e a razão da saída
  de emergência acima.
- **Remap por aplicativo exige o grupo `keyd`.** Sem ele, o `keyd bind` não alcança o socket do
  keyd; o `omarchy-key-remap status` avisa quando é esse o problema.
- **Remap por aplicativo só no Hyprland.** Os globais funcionam onde o keyd funcionar.

## Como funciona a parte por aplicativo

O Hyprland publica toda mudança de foco em
`$XDG_RUNTIME_DIR/hypr/<instância>/.socket2.sock`. O observador lê dali o
`activewindow>>classe,título` e, a cada mudança, roda `keyd bind reset` seguido dos atalhos
daquela classe. O reset é a metade importante: ele restaura exatamente o que o arquivo de
configuração diz, então um remap nunca sobrevive à janela a que pertence.

## Desenvolvimento

```bash
python -m pytest tests -q     # 69 testes, sem precisar de keyd nem de root
```

O gerador de configuração (`okeyremap/keydconf.py`) e o interpretador de teclas
(`okeyremap/keys.py`) são funções puras, e o observador recebe o `keyd bind` como parâmetro,
de modo que a lógica de foco é testável sem nenhum dos dois. A lista de teclas embutida é a
saída de `keyd list-keys` do keyd 2.6; quando o keyd está instalado, vale a lista ao vivo.

## Licença

MIT © Andre Bruno
