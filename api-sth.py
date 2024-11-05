import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz
import plotly.express as px
import pandas as pd
import json

 
# Constants for IP and port
IP_ADDRESS = "4.228.64.5"
PORT_STH = 8666
DASH_HOST = "0.0.0.0"  # Set this to "0.0.0.0" to allow access from any IP
lamp = "06x"

#variaveis 
triggerMinLum = 0
triggerMaxLum = 30
erroTotalLum=0
erroMinLum = 0
erroMaxLum = 0
valorDentroLimiteLum = 0

triggerMinTemp = 15
triggerMaxTemp = 25
erroTotalTemp=0
erroMinTemp = 0
erroMaxTemp = 0
valorDentroLimiteTemp = 0

triggerMinUmi = 30
triggerMaxUmi = 50
erroTotalUmi = 0
erroMinUmi = 0
erroMaxUmi = 0
valorDentroLimiteUmi = 0

ErroLuz = False
ErroTemp = False
ErroUmi = False

 #################################################################################
 #Functions before start
 
# Function to get data from the API
def get_data(lastN,dataType):
    #call api data
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Lamp/id/urn:ngsi-ld:Lamp:{lamp}/attributes/{dataType}?lastN={lastN}"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        try:
            values = data['contextResponses'][0]['contextElement']['attributes'][0]['values']
            return values
        except KeyError as e:
            print(f"Key error: {e}")
            return []
    else:
        print(f"Error accessing {url}: {response.status_code}")
        return []

def turn_light():
    global ErroLuz, ErroTemp, ErroUmi

    url = f"http://{IP_ADDRESS}:1026/v2/entities/urn:ngsi-ld:Lamp:{lamp}/attrs"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/',
        'Content-Type': 'application/json'  # Adicione este cabeçalho
    }
    
    if(ErroLuz == False and ErroUmi == False and ErroTemp == False ):
        estado = "off"
    else:
        estado = "on"
    
    # Defina o corpo da requisição
    payload = {
        f"{estado}": {
            "type": "command",
            "value": ""
        }
    }
    requests.patch(url, headers=headers, data=json.dumps(payload))

 
 # Function to convert UTC timestamps to São Paulo time
def convert_to_sao_paulo_time(timestamps):
    utc = pytz.utc
    lisbon = pytz.timezone('America/Sao_Paulo')
    converted_timestamps = []
    for timestamp in timestamps:
        try:
            timestamp = timestamp.replace('T', ' ').replace('Z', '')
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')).astimezone(lisbon)
        except ValueError:
            # Handle case where milliseconds are not present
            converted_time = utc.localize(datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')).astimezone(lisbon)
        converted_timestamps.append(converted_time)
    return converted_timestamps
 
# Set lastN value
lastN = 10  # Get 10 most recent points at each interval
 
 #############################################################################################################
 #Layout data
 
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
 
app.layout = html.Div([
    
    # Store to hold historical data
    dcc.Store(id='luminosity-data-store', data={'timestamps': [], 'luminosity_values': []}),
    dcc.Store(id='temperature-data-store', data={'timestamps': [], 'temperature_values': []}),
    dcc.Store(id='humidity-data-store', data={'timestamps': [], 'humidity_values': []}),
    
    html.H1('ESP 32 Data Viewer', style={'color': 'darkblue', 'font-size': '60px'}),
    html.Div([
            html.H2('Dados de Luminosidade', style={'color': 'darkblue', 'font-size': '40px'}),
            dcc.Graph(id='luminosity-graph'),
            dbc.Row([
                dbc.Col(dcc.Graph(id='luminosity-ErrorData-graph'), width=6),
                dbc.Col(dcc.Graph(id='luminosity-Pie-graph'), width=6)
            ])
        ]),

        
        #Div for temperature dashboard
        html.Div([
            html.H2('Dados de Temperatura', style={'color': 'darkblue', 'font-size': '40px'}),
            dcc.Graph(id='temperature-graph'),
            dbc.Row([
                dbc.Col(dcc.Graph(id='temperature-ErrorData-graph'),width=6 ),
                dbc.Col(dcc.Graph(id='temperature-Pie-graph'),width=6)
            ])
            
        ]),
        
        #Div for humidity dashboard
        html.Div([
            html.H2('Dados de Umidade', style={'color': 'darkblue', 'font-size': '40px'}),
            dcc.Graph(id='humidity-graph'),
            dbc.Row([
                dbc.Col(dcc.Graph(id='humidity-ErrorData-graph'),width=6 ),
                 dbc.Col(dcc.Graph(id='humidity-Pie-graph'),width=6)

            ])

        ]),

        #Update site
        dcc.Interval(
            id='interval-component',
            interval=10*1000,  # in milliseconds (10 seconds)
            n_intervals=0
        )
], style={'background-color': 'lightblue'})

    


##########################################################################################################
#Callbacks
#Get data of all data stores
@app.callback(
    Output('luminosity-data-store', 'data'),
    Output('temperature-data-store', 'data'),
    Output('humidity-data-store', 'data'),
    
    #add one input for humidity
    Input('interval-component', 'n_intervals'),
    State('luminosity-data-store', 'data'),
    State('temperature-data-store', 'data'),
    State('humidity-data-store', 'data')
)
def update_data_store(n, luminosity_data, temperature_data, humidity_data):
    global erroMaxTemp, erroMinTemp, valorDentroLimiteTemp
    global erroMaxLum, erroMinLum, valorDentroLimiteLum
    global erroMaxUmi, erroMinUmi, valorDentroLimiteUmi
    global ErroLuz, ErroTemp, ErroUmi

    luminosity_data = generic_update_data_store(n,luminosity_data,"luminosity")
        
    temperature_data = generic_update_data_store(n,temperature_data,"temperature")
    
    humidity_data = generic_update_data_store(n,humidity_data,"humidity")
    
    if temperature_data:
        
        if temperature_data["temperature_values"][-1] > triggerMaxTemp  :
            ErroTemp = True
            erroMaxTemp+=1
        elif temperature_data["temperature_values"][-1] < triggerMinTemp  :
            ErroTemp = True
            erroMinTemp+=1
        else:
            ErroTemp = False
            valorDentroLimiteTemp+=1
            
    if luminosity_data:
        
        if luminosity_data["luminosity_values"][-1] > triggerMaxLum  :
            ErroLuz = True
            erroMaxLum+=1
        elif luminosity_data["luminosity_values"][-1] < triggerMinLum  :
            ErroLuz = True
            erroMinLum+=1
        else:
            ErroLuz = False
            valorDentroLimiteLum+=1
            
    if humidity_data:
        
        if humidity_data["humidity_values"][-1] > triggerMaxUmi  :
            ErroUmi = True
            erroMaxUmi+=1
        elif humidity_data["humidity_values"][-1] < triggerMinUmi  :
            ErroUmi = True
            erroMinUmi+=1
        else:
            ErroUmi = False
            valorDentroLimiteUmi+=1
    turn_light()
    return luminosity_data, temperature_data, humidity_data


#update line graphs
@app.callback(
    Output('luminosity-graph', 'figure'),
    Output('temperature-graph', 'figure'),
    Output('humidity-graph', 'figure'),

    Input('luminosity-data-store', 'data'),
    Input('temperature-data-store', 'data'),
    Input('humidity-data-store', 'data')
)
def update_graph(luminosity_data, temperature_data, humidity_data):
    fig_luminosity = generic_update_graph(luminosity_data,"luminosity","Luminosidade","orange")
    fig_temperature = generic_update_graph(temperature_data,"temperature","Temperatura","red")
    fig_humidity = generic_update_graph(humidity_data,"humidity","Umidade","yellow")
    
    return fig_luminosity, fig_temperature, fig_humidity


#update bar graph
@app.callback(
    Output('luminosity-ErrorData-graph','figure'),
    Output('temperature-ErrorData-graph','figure'),
    Output('humidity-ErrorData-graph','figure'),

    Input('interval-component', 'n_intervals'),

)
def updateErroGraph(n):
        luminosity_histogram = generic_updateErroGraph([valorDentroLimiteLum,erroMaxLum,erroMinLum])
        temperature_histogram = generic_updateErroGraph([valorDentroLimiteTemp,erroMaxTemp,erroMinTemp])
        humidity_histogram = generic_updateErroGraph([valorDentroLimiteUmi,erroMaxUmi,erroMinUmi])
        return luminosity_histogram,temperature_histogram,humidity_histogram


@app.callback(
    Output('luminosity-Pie-graph', 'figure'),
    Output('temperature-Pie-graph', 'figure'),
    Output('humidity-Pie-graph', 'figure'),

    Input('interval-component', 'n_intervals'),
)
def UpdatePieGraph(n):
    luminosity_pie = generic_UpdatePieGraph([valorDentroLimiteLum,erroMaxLum,erroMinLum])
    temperature_pie = generic_UpdatePieGraph([valorDentroLimiteTemp,erroMaxTemp,erroMinTemp])
    humidity_pie = generic_UpdatePieGraph([valorDentroLimiteUmi,erroMaxUmi,erroMinUmi])


    return luminosity_pie,temperature_pie, humidity_pie

#############################################################################################################
#functions

#create data store for other datas
def generic_update_data_store(n, stored_data,dataType):
    # Get luminosity data
    data = get_data(lastN, dataType)

    if data:
        # Extract values and timestamps
        data_values = [float(entry['attrValue']) for entry in data]  # Ensure values are floats
        timestamps = [entry['recvTime'] for entry in data]

        # Calculate the average luminosity for the current interval
        average_data = sum(data_values) / len(data_values)

        # Convert timestamps to Lisbon time
        timestamps = convert_to_sao_paulo_time(timestamps)

        # Append the new average and the latest timestamp to stored data
        stored_data['timestamps'].append(timestamps[-1])  # Store only the latest timestamp
        stored_data[f'{dataType}_values'].append(average_data)  # Store the average luminosity

        # Calculate total average luminosity
        total_data = sum(stored_data[f'{dataType}_values'])
        total_count = len(stored_data[f'{dataType}_values'])
        stored_data[f'total_average_{dataType}'] = total_data / total_count if total_count > 0 else 0

        return stored_data
    return stored_data

#update the graph for others data
def generic_update_graph(stored_data, data_type,name, data_color):
    
    if stored_data['timestamps'] and stored_data[f'{data_type}_values']:
        # Create traces for the plot
        trace_average = go.Scatter(
            x=stored_data['timestamps'],
            y=stored_data[f'{data_type}_values'],
            mode='lines+markers',
            name=f'{name}',
            line=dict(color=data_color)
        )

        # Create a trace for the total average
        total_average = stored_data[f'total_average_{data_type}']
        trace_total_average = go.Scatter(
            x=[stored_data['timestamps'][0], stored_data['timestamps'][-1]],
            y=[total_average, total_average],
            mode='lines',
            name=f'Media da {name}',
            line=dict(color='blue', dash='dash')
        )

        # Create figure
        fig_data = go.Figure(data=[trace_average, trace_total_average])

        # Update layout
        fig_data.update_layout(
            title=f'{name}',
            xaxis_title='Timestamp',
            yaxis_title=f'{data_type}',
            hovermode='closest'
        )

        return fig_data

    return {} 


def generic_updateErroGraph(quantidades):
        # Criar um DataFrame com as quantidades
        categorias = ['Dentro do limite', 'Acima do limite', 'Abaixo do limite']
        
        df = pd.DataFrame({
            'Categoria': categorias,
            'Quantidade': quantidades
        })

        # Criar o gráfico de barras
        fig_histogram = px.bar(df, x='Categoria', y='Quantidade', text='Quantidade')

        fig_histogram.update_layout(
            title='Quantidade de valores dentro e fora do limite',
            yaxis_title='Quantidade',
            yaxis=dict(title='Quantidade', autorange=True)  
        )

        return fig_histogram

def generic_UpdatePieGraph(valores):
    # Cria os dados com as categorias e valores desejados
    ErroTotal = valores[1] + valores[2]
    Total = valores[0] + ErroTotal
    if Total == 0: 
        Total = 1
    data = {
        "names": ["Dentro do Limite", "Fora do limite"],
        "values": [ valores[0]*100/Total, ErroTotal*100/Total]
    }
    
    # Converte o dicionário em um DataFrame
    df = pd.DataFrame(data)
    
    # Gera o gráfico de pizza
    fig = px.pie(df, values="values", names="names", hole=.3)
    return fig


    
###########################################################################################################################
#Run server
if __name__ == '__main__':
    app.run_server(debug=True, host=DASH_HOST, port=8040)