import streamlit as st
import cartolafc
import pandas as pd
import altair as alt

# Configuração da página para ficar bonita no celular
st.set_page_config(page_title="Cartola Turnos", layout="centered", initial_sidebar_state="collapsed")

st.title("🏆 AT NIGHT'S LEAGUE - TURNOS")

# O st.cache_data evita que o app fique consultando a API a cada clique, guardando os dados por 1 hora.
@st.cache_data(ttl=3600)
def carregar_dados():
    cartola = cartolafc.Api()
    
    id_times = [29674391,14156535,12039729,25577506,25330326,49127596,8812795,24326206]
    rodada_atual = cartola.mercado().rodada_atual
    
    dados_rodadas = []
    
    # Busca os dados rodada por rodada para cada time
    for id_time in id_times:
        # range(1, rodada_atual) pega desde a rodada 1 até a última rodada fechada
        for rodada in range(1, rodada_atual):
            try:
                time = cartola.time(id_time, rodada)
                pontos = time.ultima_pontuacao
                
                # Desconto do capitão (regra específica do seu código)
                for atleta in time.atletas:   
                    if atleta.is_capitao is True:
                        pontos -= atleta.pontos * 0.5
                
                # Calcula a qual turno essa rodada pertence (considerando 7 rodadas por turno)
                turno = ((rodada - 1) // 7) + 1
                
                dados_rodadas.append({
                    "Time": time.info.slug,
                    "Turno": turno,
                    "Rodada": rodada,
                    "Pontos": pontos
                })
            except Exception as e:
                # Se der erro em alguma rodada (ex: time não escalou), simplesmente continua
                continue
                
    # Cria o DataFrame com todo o histórico
    df = pd.DataFrame(dados_rodadas)
    return df, rodada_atual

# --- Início da Interface ---
st.write("Buscando os dados mais recentes na API do Cartola...")

try:
    with st.spinner('Calculando pontuações. Isso pode levar alguns segundos...'):
        df_todas_rodadas, rodada_atual = carregar_dados()
    
    st.success(f"Dados carregados! Rodada Atual do Mercado: **{rodada_atual}**")

    # Verifica se a API retornou dados corretamente
    if df_todas_rodadas.empty:
        st.warning("Nenhum dado encontrado. O campeonato já começou?")
    else:
        # Criando as opções de turno e adicionando a opção "Geral"
        lista_turnos = sorted(df_todas_rodadas['Turno'].unique().tolist())
        opcoes_filtro = ["Geral"] + [f"Turno {t}" for t in lista_turnos]
        
        # Caixa de seleção para o usuário escolher
        escolha = st.selectbox("Selecione o Turno para visualizar", options=opcoes_filtro)

        # Filtra os dados de acordo com a seleção (Geral ou um Turno específico)
        if escolha == "Geral":
            st.subheader("🏆 Classificação Geral (Soma de todos os turnos)")
            df_filtrado = df_todas_rodadas.copy()
        else:
            turno_selecionado = int(escolha.split(" ")[1]) # Pega o número do turno na string
            st.subheader(f"📊 Classificação - Turno {turno_selecionado}")
            df_filtrado = df_todas_rodadas[df_todas_rodadas['Turno'] == turno_selecionado].copy()

        # ==========================================
        # 1. TABELA DE CLASSIFICAÇÃO
        # ==========================================
        # Agrupa os pontos pelo total daquele período
        df_tabela = df_filtrado.groupby('Time', as_index=False)['Pontos'].sum()
        
        # Ordena a pontuação do maior para o menor
        df_tabela = df_tabela.sort_values(by="Pontos", ascending=False).reset_index(drop=True)
        df_tabela['Pontos'] = df_tabela['Pontos'].round(2)

        # Calcula a diferença para o líder
        pontuacao_lider = df_tabela['Pontos'].iloc[0]
        df_tabela['Diferença para o Líder'] = (pontuacao_lider - df_tabela['Pontos']).round(2)

        # Ajusta Posições e Renomeia
        df_tabela.index = df_tabela.index + 1
        df_tabela.index.name = "Posição"
        df_tabela = df_tabela.rename(columns={'Pontos': 'Pontuação'})

        st.write("📋 **Tabela de Classificação**")
        st.dataframe(df_tabela, use_container_width=True)

        # ==========================================
        # 2. GRÁFICO DE EVOLUÇÃO (LINHAS)
        # ==========================================
        # Ordena por rodada e calcula a "Soma Acumulada" (cumsum)
        df_grafico = df_filtrado.sort_values(by=['Time', 'Rodada'])
        df_grafico['Pontuação Acumulada'] = df_grafico.groupby('Time')['Pontos'].cumsum().round(2)

        # Cria o Gráfico Altair
        grafico_evolucao = alt.Chart(df_grafico).mark_line(point=True).encode(
            x=alt.Y('Rodada:O', title='Rodada'), 
            y=alt.X('Pontuação Acumulada:Q', title='Pontuação Acumulada', scale=alt.Scale(zero=False)),
            color=alt.Color('Time:N', title='Time'),
            # No tooltip, adicionei também a pontuação que ele fez só naquela rodada específica!
            tooltip=['Time', 'Rodada', 'Pontuação Acumulada', alt.Tooltip('Pontos:Q', title='Pontos na Rodada')]
        ).properties(
            height=400,
            title="Evolução da Pontuação Acumulada"
        ).interactive() 
        
        st.altair_chart(grafico_evolucao, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao buscar os dados: {e}")

# Botão para forçar a atualização dos dados da API
st.divider()
if st.button("🔄 Atualizar Dados Agora"):
    carregar_dados.clear() # Limpa o cache
    st.rerun() # Recarrega a página