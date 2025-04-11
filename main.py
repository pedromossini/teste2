import streamlit as st
import requests
import json
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from google.generativeai import configure, GenerativeModel
import re

# Configuração das chaves de API
MY_SHIP_TRACKING_API_KEY = os.environ.get("MY_SHIP_TRACKING_API_KEY", "SUA_CHAVE_API_MYSHIPTRACKING")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "SUA_CHAVE_API_GEMINI")

# Configurar a API do Google Gemini
configure(api_key=GOOGLE_API_KEY)
gemini_model = GenerativeModel('gemini-pro')

class ShippingAnalyzer:
    def __init__(self, myship_api_key, gemini_model):
        """Inicializa o analisador de tráfego marítimo."""
        self.myship_api_key = myship_api_key
        self.base_url = "https://api.myshiptracking.com/v1"
        self.gemini_model = gemini_model
        
    def get_ships_near_port(self, port_name):
        """Obtém navios próximos a um porto específico."""
        # Primeiro, buscar o porto pelo nome
        port_endpoint = f"{self.base_url}/ports"
        
        port_params = {
            "api_key": self.myship_api_key,
            "name": port_name
        }
        
        try:
            port_response = requests.get(port_endpoint, params=port_params)
            
            if port_response.status_code != 200:
                return {"error": f"Failed to fetch port data: {port_response.status_code}"}
            
            port_data = port_response.json()
            
            if not port_data or len(port_data) == 0:
                return {"error": f"No ports found with name: {port_name}"}
            
            # Usar o primeiro porto encontrado
            port = port_data[0]
            
            # Agora buscar navios ativos que têm este porto como destino ou origem
            vessels_endpoint = f"{self.base_url}/vessels"
            
            vessels_params = {
                "api_key": self.myship_api_key,
                "name": ""  # Busca ampla
            }
            
            vessels_response = requests.get(vessels_endpoint, params=vessels_params)
            
            if vessels_response.status_code != 200:
                return {"error": f"Failed to fetch vessels data: {vessels_response.status_code}"}
            
            all_vessels = vessels_response.json()
            
            # Filtrar apenas navios relacionados ao porto
            port_related_vessels = []
            
            for vessel in all_vessels:
                if vessel.get("destination") == port_name or vessel.get("last_port") == port_name:
                    port_related_vessels.append(vessel)
            
            return {"ships": port_related_vessels, "port": port}
        except Exception as e:
            return {"error": f"Error fetching data: {str(e)}"}
    
    def get_ship_by_mmsi(self, mmsi):
        """Obtém detalhes de um navio específico pelo MMSI."""
        vessel_endpoint = f"{self.base_url}/vessels/{mmsi}"
        
        vessel_params = {
            "api_key": self.myship_api_key
        }
        
        try:
            vessel_response = requests.get(vessel_endpoint, params=vessel_params)
            
            if vessel_response.status_code != 200:
                return {"error": f"Failed to fetch vessel data: {vessel_response.status_code}"}
            
            vessel_data = vessel_response.json()
            
            return {"ship": vessel_data}
        except Exception as e:
            return {"error": f"Error fetching data: {str(e)}"}
    
    def search_vessels(self, query, limit=10):
        """Pesquisa navios por nome, tipo, bandeira, etc."""
        vessels_endpoint = f"{self.base_url}/vessels"
        
        vessels_params = {
            "api_key": self.myship_api_key,
            "name": query
        }
        
        try:
            vessels_response = requests.get(vessels_endpoint, params=vessels_params)
            
            if vessels_response.status_code != 200:
                return {"error": f"Failed to fetch vessels data: {vessels_response.status_code}"}
            
            all_vessels = vessels_response.json()
            
            # Limitar o número de resultados
            limited_vessels = all_vessels[:limit] if len(all_vessels) > limit else all_vessels
            
            return {"ships": limited_vessels}
        except Exception as e:
            return {"error": f"Error fetching data: {str(e)}"}
    
    def get_port_info(self, port_name):
        """Obtém informações detalhadas sobre um porto específico."""
        port_endpoint = f"{self.base_url}/ports"
        
        port_params = {
            "api_key": self.myship_api_key,
            "name": port_name
        }
        
        try:
            port_response = requests.get(port_endpoint, params=port_params)
            
            if port_response.status_code != 200:
                return {"error": f"Failed to fetch port data: {port_response.status_code}"}
            
            port_data = port_response.json()
            
            if not port_data or len(port_data) == 0:
                return {"error": f"No ports found with name: {port_name}"}
            
            # Usar o primeiro porto encontrado
            port = port_data[0]
            
            return {"port": port}
        except Exception as e:
            return {"error": f"Error fetching data: {str(e)}"}
    
    def get_ships_in_area(self, latitude, longitude, radius=50):
        """Obtém navios em uma área específica (dados simulados)."""
        # Dados simulados para demonstração
        ship_types = ["Cargo", "Tanker", "Passenger", "Fishing", "Tug", "Pleasure Craft"]
        ship_flags = ["Panama", "Liberia", "Marshall Islands", "Singapore", "Malta", "Bahamas"]
        ports = ["Rotterdam", "Singapore", "Shanghai", "Antwerp", "Hamburg", "Los Angeles"]
        statuses = ["Underway using engine", "At anchor", "Moored", "Stopped", "Restricted maneuverability"]
        
        # Gerar entre 5 e 15 navios aleatórios
        num_ships = random.randint(5, 15)
        ships = []
        
        for i in range(num_ships):
            # Gera dados aleatórios para cada navio
            ship = {
                "mmsi": str(random.randint(100000000, 999999999)),
                "name": f"VESSEL {random.randint(1000, 9999)}",
                "type": random.choice(ship_types),
                "speed": round(random.uniform(0, 20), 1),
                "course": round(random.uniform(0, 359), 1),
                "latitude": latitude + (random.random() - 0.5) * (radius/50),
                "longitude": longitude + (random.random() - 0.5) * (radius/50),
                "flag": random.choice(ship_flags),
                "destination": random.choice(ports),
                "status": random.choice(statuses)
            }
            ships.append(ship)
        
        return {
            "ships": ships, 
            "note": "Dados simulados para demonstração. API MyShipTracking não suporta busca por área geográfica."
        }
    
    def analyze_query(self, query):
        """Analisa a consulta do usuário para determinar a intenção e extrair parâmetros relevantes."""
        query = query.lower()
        
        # Padrões de reconhecimento para vários tipos de consultas
        port_patterns = [
            r'porto\s+de\s+([a-zA-Z\s]+)',
            r'porto\s+([a-zA-Z\s]+)',
            r'portos?\s+em\s+([a-zA-Z\s]+)',
            r'portos?\s+próximos?\s+a\s+([a-zA-Z\s]+)',
            r'harbour\s+of\s+([a-zA-Z\s]+)',
            r'port\s+of\s+([a-zA-Z\s]+)'
        ]
        
        vessel_patterns = [
            r'navio\s+([a-zA-Z0-9\s]+)',
            r'embarcação\s+([a-zA-Z0-9\s]+)',
            r'vessel\s+([a-zA-Z0-9\s]+)',
            r'ship\s+([a-zA-Z0-9\s]+)'
        ]
        
        mmsi_patterns = [
            r'mmsi\s*[:\-]?\s*(\d{9})',
            r'mmsi\s+(\d{9})'
        ]
        
        region_patterns = [
            r'região\s+de\s+([a-zA-Z\s]+)',
            r'área\s+de\s+([a-zA-Z\s]+)',
            r'próximo\s+a\s+([a-zA-Z\s]+)',
            r'perto\s+de\s+([a-zA-Z\s]+)',
            r'region\s+of\s+([a-zA-Z\s]+)',
            r'near\s+([a-zA-Z\s]+)'
        ]
        
        vessel_type_patterns = [
            r'navios?\s+do\s+tipo\s+([a-zA-Z\s]+)',
            r'navios?\s+([a-zA-Z\s]+)',
            r'embarcações?\s+do\s+tipo\s+([a-zA-Z\s]+)',
            r'embarcações?\s+([a-zA-Z\s]+)',
            r'ships?\s+of\s+type\s+([a-zA-Z\s]+)',
            r'([a-zA-Z\s]+)\s+ships'
        ]
        
        flag_patterns = [
            r'bandeira\s+d[eo]\s+([a-zA-Z\s]+)',
            r'flag\s+of\s+([a-zA-Z\s]+)'
        ]
        
        # Tentar identificar a intenção principal e extrair parâmetros
        intent = "general"
        params = {}
        
        # Verificar portos
        for pattern in port_patterns:
            match = re.search(pattern, query)
            if match:
                intent = "port_info"
                params["port_name"] = match.group(1).strip()
                break
        
        # Verificar navios por nome
        if intent == "general":
            for pattern in vessel_patterns:
                match = re.search(pattern, query)
                if match:
                    intent = "vessel_search"
                    params["query"] = match.group(1).strip()
                    break
        
        # Verificar navios por MMSI
        if intent == "general":
            for pattern in mmsi_patterns:
                match = re.search(pattern, query)
                if match:
                    intent = "vessel_by_mmsi"
                    params["mmsi"] = match.group(1).strip()
                    break
        
        # Verificar regiões
        if intent == "general":
            for pattern in region_patterns:
                match = re.search(pattern, query)
                if match:
                    region_name = match.group(1).strip()
                    # Verificar se a região corresponde a alguma região conhecida
                    regions = {
                        "suez": {"name": "Canal de Suez", "lat": 30.4276, "lon": 32.3439},
                        "gibraltar": {"name": "Estreito de Gibraltar", "lat": 35.9897, "lon": -5.6125},
                        "panama": {"name": "Canal do Panamá", "lat": 9.1480, "lon": -79.8308},
                        "malaca": {"name": "Estreito de Malaca", "lat": 1.7136, "lon": 101.4661},
                        "roterdã": {"name": "Porto de Roterdã", "lat": 51.9244, "lon": 4.4777},
                        "rotterdam": {"name": "Porto de Roterdã", "lat": 51.9244, "lon": 4.4777},
                        "brasil": {"name": "Costa do Brasil", "lat": -23.9619, "lon": -46.3042},
                        "brazil": {"name": "Costa do Brasil", "lat": -23.9619, "lon": -46.3042},
                        "los angeles": {"name": "Porto de Los Angeles", "lat": 33.7283, "lon": -118.2712},
                        "shanghai": {"name": "Porto de Shanghai", "lat": 31.2304, "lon": 121.4737}
                    }
                    
                    for key, value in regions.items():
                        if key in region_name.lower():
                            intent = "ships_in_area"
                            params["lat"] = value["lat"]
                            params["lon"] = value["lon"]
                            params["region_name"] = value["name"]
                            break
                    
                    if intent == "general":
                        # Se não encontrou uma região conhecida, tente usar como nome de porto
                        intent = "port_info"
                        params["port_name"] = region_name
                    
                    break
        
        # Verificar tipos de navios
        if intent == "general":
            for pattern in vessel_type_patterns:
                match = re.search(pattern, query)
                if match:
                    vessel_type = match.group(1).strip()
                    # Verificar se é um tipo de navio conhecido
                    vessel_types = {
                        "cargo": "Cargo",
                        "carga": "Cargo",
                        "passageiros": "Passenger",
                        "passenger": "Passenger",
                        "petroleiro": "Tanker",
                        "tanker": "Tanker",
                        "pesca": "Fishing",
                        "fishing": "Fishing",
                        "rebocador": "Tug",
                        "tug": "Tug",
                        "pleasure": "Pleasure Craft",
                        "recreio": "Pleasure Craft"
                    }
                    
                    for key, value in vessel_types.items():
                        if key in vessel_type.lower():
                            intent = "vessel_type_search"
                            params["vessel_type"] = value
                            break
                    
                    if intent == "general":
                        # Se não encontrou um tipo conhecido, tente pesquisar mesmo assim
                        intent = "vessel_type_search"
                        params["vessel_type"] = vessel_type
                    
                    break
        
        # Verificar bandeiras
        if intent == "general":
            for pattern in flag_patterns:
                match = re.search(pattern, query)
                if match:
                    flag = match.group(1).strip()
                    intent = "flag_search"
                    params["flag"] = flag
                    break
        
        # Se ainda estiver como "general", considerar como uma consulta geral para o Gemini
        
        return {
            "intent": intent,
            "params": params
        }
    
    def execute_query(self, query_analysis):
        """Executa a consulta com base na análise da intenção."""
        intent = query_analysis["intent"]
        params = query_analysis["params"]
        
        # Executar a ação adequada com base na intenção
        if intent == "port_info":
            return self.get_port_info(params["port_name"])
        elif intent == "vessel_search":
            return self.search_vessels(params["query"])
        elif intent == "vessel_by_mmsi":
            return self.get_ship_by_mmsi(params["mmsi"])
        elif intent == "ships_in_area":
            return self.get_ships_in_area(params["lat"], params["lon"])
        elif intent == "vessel_type_search":
            # Neste caso, simulamos dados de navios com o tipo específico
            # Em uma implementação real, seria necessário uma API que suporte filtragem por tipo
            ships_data = self.get_ships_in_area(0, 0)  # Coordenadas genéricas
            filtered_ships = [ship for ship in ships_data.get("ships", []) if ship.get("type", "").lower() == params["vessel_type"].lower()]
            return {"ships": filtered_ships}
        elif intent == "flag_search":
            # Similar ao anterior, simulamos dados com a bandeira especificada
            ships_data = self.get_ships_in_area(0, 0)
            filtered_ships = [ship for ship in ships_data.get("ships", []) if params["flag"].lower() in ship.get("flag", "").lower()]
            return {"ships": filtered_ships}
        else:
            # Para consultas gerais, não temos dados específicos para buscar
            return {"message": "Consulta geral", "intent": intent}
    
    def generate_response(self, query, query_result):
        """Gera uma resposta com base nos resultados da consulta e usa o Gemini para formatação."""
        # Base do prompt para o Gemini
        maritime_context = """
        Você é um especialista em transporte marítimo com vasto conhecimento sobre navios, portos, rotas marítimas,
        tecnologias de navegação, regulamentações internacionais e operações portuárias. Sua expertise inclui todas
        as classes de embarcações, desde grandes navios porta-contêineres até pequenas embarcações de pesca.
        
        Você deve SEMPRE:
        - Fornecer informações precisas e atualizadas sobre o transporte marítimo
        - Manter um tom profissional mas acessível
        - Incluir detalhes relevantes que enriqueçam a compreensão do usuário
        - Responder exclusivamente sobre temas relacionados ao transporte marítimo
        
        Você NUNCA deve:
        - Falar sobre temas não relacionados ao transporte marítimo ou assuntos adjacentes
        - Inventar informações que não estejam nos dados fornecidos
        - Usar linguagem excessivamente técnica sem explicação
        """
        
        # Formatar o prompt específico com base nos resultados da consulta
        if "ships" in query_result and len(query_result["ships"]) > 0:
            ships = query_result["ships"]
            
            prompt_text = f"""
            {maritime_context}
            
            O usuário perguntou: "{query}"
            
            Encontrei os seguintes dados de navios:
            {json.dumps(ships[:5] if len(ships) > 5 else ships, indent=2, ensure_ascii=False)}
            
            Total de navios encontrados: {len(ships)}
            
            Por favor, analise esses dados e responda à pergunta do usuário de forma completa e informativa.
            Destaque informações relevantes como os tipos predominantes, bandeiras comuns, e outros padrões notáveis.
            Se houver muitos navios, faça um resumo dos dados em vez de listar todos.
            """
                
        elif "port" in query_result:
            port = query_result["port"]
            
            prompt_text = f"""
            {maritime_context}
            
            O usuário perguntou: "{query}"
            
            Encontrei as seguintes informações sobre o porto:
            {json.dumps(port, indent=2, ensure_ascii=False)}
            
            Por favor, analise esses dados e responda à pergunta do usuário de forma completa e informativa.
            Inclua informações relevantes sobre a localização, importância e características do porto.
            ""
        elif "ship" in query_result:
            ship = query_result["ship"]
            
            prompt_text = f"""
            {maritime_context}
            
            O usuário perguntou: "{query}"
            
            Encontrei as seguintes informações sobre o navio:
            {json.dumps(ship, indent=2, ensure_ascii=False)}
            
            Por favor, analise esses dados e responda à pergunta do usuário de forma completa e informativa.
            Destaque informações importantes como tipo, bandeira, posição atual e destino.
            """
        else:
            prompt_text = f"""
            {maritime_context}
            
            O usuário perguntou: "{query}"
            
            Não consegui classificar adequadamente esta consulta ou encontrar dados relevantes.
            
            Por favor, responda educadamente, sugerindo que o usuário reformule a pergunta de forma mais
            específica, mencionando portos, navios, regiões marítimas ou outros termos relacionados ao 
            transporte marítimo.
            ""
        
        try:
            response = self.gemini_model.generate_content(prompt_text)
            return response.text
        except Exception as e:
            # Fallback para casos onde o Gemini falha
            if "error" in query_result:
                return f"Desculpe, não consegui processar sua consulta. Ocorreu um erro: {query_result['error']}"
            elif "ships" in query_result and len(query_result["ships"]) > 0:
                ships = query_result["ships"]
                response = f"Encontrei {len(ships)} navios relacionados à sua consulta. "
                if len(ships) <= 5:
                    for ship in ships:
                        response += f"\n\n• {ship.get('name', 'Desconhecido')} (MMSI: {ship.get('mmsi', 'Desconhecido')})"
                        response += f"\n  Tipo: {ship.get('type', 'Desconhecido')}"
                        response += f"\n  Bandeira: {ship.get('flag', 'Desconhecido')}"
                        response += f"\n  Destino: {ship.get('destination', 'Desconhecido')}"
                else:
                    response += "Aqui estão os primeiros 5:\n\n"
                    for ship in ships[:5]:
                        response += f"• {ship.get('name', 'Desconhecido')} (MMSI: {ship.get('mmsi', 'Desconhecido')})"
                        response += f"\n  Tipo: {ship.get('type', 'Desconhecido')}"
                        response += f"\n  Bandeira: {ship.get('flag', 'Desconhecido')}"
                        response += f"\n  Destino: {ship.get('destination', 'Desconhecido')}\n\n"
                return response
            else:
                return "Desculpe, não consegui processar sua consulta. Por favor, tente reformular sua pergunta sobre transporte marítimo."

def create_chat_app():
    """Cria a aplicação de chat marítimo com Streamlit."""
    st.set_page_config(page_title="Chat Marítimo", page_icon="🚢", layout="wide")
    
    st.title("🚢 Chat Marítimo")
    st.write("Converse comigo sobre qualquer aspecto do transporte marítimo. Posso fornecer informações sobre navios, portos, rotas e mais!")
    
    # Inicializar o analisador
    analyzer = ShippingAnalyzer(MY_SHIP_TRACKING_API_KEY, gemini_model)
    
    # Inicializar histórico de chat se não existir
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Olá! Sou seu assistente especializado em transporte marítimo. Como posso ajudá-lo hoje? Você pode me perguntar sobre navios específicos, portos, rotas marítimas e muito mais."}
        ]
    
    # Exibir histórico de chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Receber nova mensagem do usuário
    if query := st.chat_input("Pergunte algo sobre transporte marítimo..."):
        # Adicionar mensagem do usuário ao histórico
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Exibir mensagem do usuário
        with st.chat_message("user"):
            st.markdown(query)
        
        # Gerar resposta
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Analisando sua pergunta...")
            
            try:
                # Analisar a intenção da consulta
                query_analysis = analyzer.analyze_query(query)
                
                # Executar a consulta com base na análise
                query_result = analyzer.execute_query(query_analysis)
                
                # Gerar resposta com o Gemini
                response = analyzer.generate_response(query, query_result)
                
                # Atualizar placeholder com a resposta
                message_placeholder.markdown(response)
                
                # Adicionar resposta ao histórico
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Se houver dados de navios, oferecer visualização
                if "ships" in query_result and len(query_result["ships"]) > 0 and "note" not in query_result:
                    show_viz = st.button("📊 Visualizar dados dos navios")
                    
                    if show_viz:
                        # Criar DataFrame para visualização
                        ships = query_result["ships"]
                        
                        if len(ships) > 0:
                            with st.expander("Visualização de Dados", expanded=True):
                                # Preparar dados para visualização
                                ships_df = pd.DataFrame([
                                    {
                                        "nome": ship.get("name", "Desconhecido"),
                                        "mmsi": ship.get("mmsi", "Desconhecido"),
                                        "tipo": ship.get("type", "Desconhecido"),
                                        "bandeira": ship.get("flag", "Desconhecido"),
                                        "velocidade": ship.get("speed", 0),
                                        "curso": ship.get("course", 0),
                                        "latitude": ship.get("latitude"),
                                        "longitude": ship.get("longitude"),
                                        "destino": ship.get("destination", "Desconhecido"),
                                        "status": ship.get("status", "Desconhecido")
                                    }
                                    for ship in ships if ship.get("name")
                                ])
                                
                                # Mostrar tabela
                                st.dataframe(ships_df)
                                
                                # Layout em colunas para gráficos
                                viz_col1, viz_col2 = st.columns(2)
                                
                                # Verificar se há dados suficientes para visualizações
                                if len(ships_df) > 0:
                                    with viz_col1:
                                        # Contagem por tipo
                                        type_counts = ships_df["tipo"].value_counts().reset_index()
                                        type_counts.columns = ["Tipo de Navio", "Contagem"]
                                        
                                        fig_types = px.pie(
                                            type_counts, 
                                            values="Contagem", 
                                            names="Tipo de Navio",
                                            title="Distribuição por Tipo de Navio"
                                        )
                                        st.plotly_chart(fig_types, use_container_width=True)
                                    
                                    with viz_col2:
                                        # Contagem por bandeira
                                        flag_counts = ships_df["bandeira"].value_counts().reset_index()
                                        flag_counts.columns = ["Bandeira", "Contagem"]
                                        
                                        fig_flags = px.bar(
                                            flag_counts, 
                                            x="Bandeira", 
                                            y="Contagem",
                                            title="Distribuição por Bandeira"
                                        )
                                        st.plotly_chart(fig_flags, use_container_width=True)
                                    
                                    # Mapa (se houver coordenadas)
                                    if "latitude" in ships_df.columns and "longitude" in ships_df.columns:
                                        map_data = ships_df.dropna(subset=["latitude", "longitude"])
                                        
                                        if len(map_data) > 0:
                                            st.subheader("Mapa de Localização dos Navios")
                                            
                                            fig_map = px.scatter_mapbox(
                                                map_data,
                                                lat="latitude",
                                                lon="longitude",
                                                hover_name="nome",
                                                hover_data=["tipo", "velocidade", "bandeira", "destino"],
                                                color="tipo",
                                                zoom=3,
                                                height=500
                                            )
                                            
                                            fig_map.update_layout(
                                                mapbox_style="open-street-map",
                                                margin={"r":0,"t":0,"l":0,"b":0}
                                            )
                                            
                                            st.plotly_chart(fig_map, use_container_width=True)
            except Exception as e:
                message_placeholder.markdown(f"Desculpe, ocorreu um erro ao processar sua consulta: {str(e)}. Por favor, tente novamente ou reformule sua pergunta.")
                st.session_state.messages.append({"role": "assistant", "content": f"Desculpe, ocorreu um erro ao processar sua consulta: {str(e)}. Por favor, tente novamente ou reformule sua pergunta."})
    
    # Rodapé
    st.markdown("---")
    st.caption("Chat Marítimo desenvolvido com Streamlit, API MyShipTracking e Gemini AI. Versão 1.0")

# Função principal
if __name__ == "__main__":
    create_chat_app()
