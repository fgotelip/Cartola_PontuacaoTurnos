import streamlit as st
import cartolafc
import pandas as pd
import altair as alt

# Configuração da página para ficar bonita no celular
st.set_page_config(page_title="Cartola Turnos", layout="centered", initial_sidebar_state="collapsed")

st.title("🏆 AT NIGHT'S LEAGUE - TURNOS")

# O st.cache_data evita que o app fique consultando a API a cada clique, guardando os dados por 1 hora.
# O botão "Atualizar" no final do app limpa esse cache e força a busca de novos dados.
@st.cache_data(ttl=3600)
def carregar_dados():
    cartola = cartolafc.Api()

    def gera_pontuacao_turno(id_times,num_turno,pontuacoes_por_turno,rodada_inicial,rodada_final):
        for id in id_times:
            pontuacao = 0
            for rodada in range(rodada_inicial,rodada_final):
                time = cartola.time(id,rodada)
                pontuacao += time.ultima_pontuacao
                
                for atleta in time.atletas:   
                    if atleta.is_capitao is True:
                        pontuacao -= atleta.pontos*0.5
            
            time_pontuacao = {"turno":num_turno,"time":time.info.slug,"pontuacao":pontuacao}
            pontuacoes_por_turno.append(time_pontuacao)
        return pontuacoes_por_turno

    def gera_turnos(qtd_rodadas,valor,parametro=0):
        if parametro == 0:
            turnos=[]
            qtd_turnos = int(qtd_rodadas/valor)
            for i in range(qtd_turnos):
                rodada_inical = i*valor + 1
                rodada_final = rodada_inical+valor
                turnos.append((rodada_inical,rodada_final))
            return turnos

    def gera_pontuacoes_por_turno(id_times,rodada_atual,qtd_rodadas,valor,parametro=0):
        turnos = gera_turnos(qtd_rodadas,valor,parametro)
        pontuacoes_por_turno = []
        num_turno = 1
        for turno in turnos:
            if turno[0] > rodada_atual:
                break
            if turno[1] >= rodada_atual:
                gera_pontuacao_turno(id_times,num_turno,pontuacoes_por_turno,turno[0],rodada_atual)
                break
            gera_pontuacao_turno(id_times,num_turno,pontuacoes_por_turno,turno[0],turno[1])
            num_turno+=1
        return pontuacoes_por_turno,turnos

    id_times = [29674391,14156535,12039729,25577506,25330326,49127596,8812795,24326206]
    rodada_atual = cartola.mercado().rodada_atual
    qtd_rodadas = 38
    qtd_rodadas_por_turno = 7

    pontuacoes,turnos = gera_pontuacoes_por_turno(id_times,rodada_atual,qtd_rodadas,qtd_rodadas_por_turno)
    df = pd.DataFrame(pontuacoes)
    return df, rodada_atual,turnos

# --- Início da Interface ---
st.write("Buscando os dados mais recentes na API do Cartola...")

try:
    with st.spinner('Calculando pontuações. Isso pode levar alguns segundos...'):
        df_turnos, rodada_atual,turnos = carregar_dados()

    # Criando as opções de turno e adicionando a opção "Geral"
    lista_turnos = df_turnos['turno'].unique().tolist()
    opcoes_filtro = ["Geral"] + lista_turnos
    turno_atual = lista_turnos[-1]

    rodada_atual_turno = rodada_atual - turnos[turno_atual-1][0]

    st.success(f"Dados carregados! Rodada Atual: **{rodada_atual}**")

    # Caixa de seleção para o usuário escolher
    turno_selecionado = st.selectbox("Selecione o Turno para visualizar", options=opcoes_filtro)

    # Lógica para somar e ordenar dependendo da escolha
    if turno_selecionado == "Geral":
        st.subheader("🏆 Classificação Geral (Soma de todos os turnos)")
        # Agrupa pelos times e soma as pontuações de todos os turnos
        df_exibicao = df_turnos.groupby('time', as_index=False)['pontuacao'].sum()
    else:
        st.subheader(f"📊 Classificação - Turno {turno_selecionado}")
        st.subheader(f"Rodada {rodada_atual_turno} de 7 - restam {7-rodada_atual_turno} rodadas")
        # Filtra o DataFrame apenas para o turno escolhido
        df_exibicao = df_turnos[df_turnos['turno'] == turno_selecionado]
        
        # Remove a coluna 'turno' para limpar a tabela
        df_exibicao = df_exibicao.drop(columns=['turno'])

    # Ordena a pontuação em ordem decrescente (do maior para o menor)
    df_exibicao = df_exibicao.sort_values(by="pontuacao", ascending=False).reset_index(drop=True)
    
    # Arredonda a pontuação para 2 casas decimais para ficar mais limpo
    df_exibicao['pontuacao'] = df_exibicao['pontuacao'].round(2)

    # --- NOVIDADE: Calcula a diferença para o líder ---
    # Como os dados já estão ordenados, o líder é a primeira linha (índice 0)
    pontuacao_lider = df_exibicao['pontuacao'].iloc[0]
    
    # Cria a nova coluna subtraindo a pontuação de cada time da pontuação do líder
    df_exibicao['diferença_lider'] = (pontuacao_lider - df_exibicao['pontuacao']).round(2)

    # Ajusta o índice para servir como "Posição" no campeonato (começando do 1)
    df_exibicao.index = df_exibicao.index + 1
    df_exibicao.index.name = "Pos"

    df_exibicao = df_exibicao.rename(columns={
        'time': 'Time', 
        'pontuacao': 'P',
        'diferença_lider': 'Dif Líder' # Ajuste aqui se a sua coluna se chamar 'diferença pro líder'
    })

    
    # 1. Mostrar Tabela de Classificação
    st.write("📋 **Tabela de Classificação**")

    st.dataframe(df_exibicao, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao buscar os dados: {e}")

# Botão para forçar a atualização dos dados da API
st.divider()
if st.button("🔄 Atualizar Dados Agora"):
    carregar_dados.clear() # Limpa o cache
    st.rerun() # Recarrega a página