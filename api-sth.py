import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz
import plotly.express as px
import pandas as pd

 
# Constants for IP and port
IP_ADDRESS = "4.228.64.5"
PORT_STH = 8666
DASH_HOST = "0.0.0.0"  # Set this to "0.0.0.0" to allow access from any IP
lamp = "05x"

#variaveis 
triggerMinLum = 0
triggerMaxLum = 30
erroTotalLum=0
erroMinLum = 0
erroMaxLum = 0
valorDentroLimiteLum = 0

triggerMinTemp = 0
triggerMaxTemp = 30
erroTotalTemp=0
erroMinTemp = 0
erroMaxTemp = 0
valorDentroLimiteTemp = 0
 
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
    url = f"http://{url}:1026/v2/entities/urn:ngsi-ld:Lamp:{lamp}/attrs"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/'
    }
    requests.patch(url, headers=headers)

 
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
 
app = dash.Dash(__name__)
 
app.layout = html.Div([
    
    # Store to hold historical data
    dcc.Store(id='luminosity-data-store', data={'timestamps': [], 'luminosity_values': []}),
    dcc.Store(id='temperature-data-store', data={'timestamps': [], 'temperature_values': []}),
    dcc.Store(id='humidity-data-store', data={'timestamps': [], 'humidity': []}),
    
    html.H1('ESP 32 Data Viewer'),
    
    #Div for luminosity dashboard
    html.Div([
        html.H2('Dados de Luminosidade'),

        dcc.Graph(id='luminosity-graph'),
        dcc.Graph(id='luminosity-ErrorData-graph')


    ]),
    
    #Div for temperature dashboard
    html.Div([
        html.H2('Dados de Temperatura'),
        dcc.Graph(id='temperature-graph'),
        dcc.Graph(id='temperature-ErrorData-graph')

    ]),
    
    #Div for humidity dashboard
    html.Div([
        html.H2('Dados de Umidade'),
        dcc.Graph(id='humidity-graph'),

    ]),
    

    #Update site
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # in milliseconds (10 seconds)
        n_intervals=0
    )
    
])

##########################################################################################################
#Callbacks
#Get data of all data stores
@app.callback(
    Output('luminosity-data-store', 'data'),
    Output('temperature-data-store', 'data'),
    #add one output for humidity
    Input('interval-component', 'n_intervals'),
    State('luminosity-data-store', 'data'),
    State('temperature-data-store', 'data')
    #add one input for humidity
)
def update_data_store(n, luminosity_data, temperature_data):
    global erroMaxTemp, erroMinTemp, valorDentroLimiteTemp
    global erroMaxLum, erroMinLum, valorDentroLimiteLum

    luminosity_data = generic_update_data_store(n,luminosity_data,"luminosity")
        
    temperature_data = generic_update_data_store(n,temperature_data,"temperature")
    
    if temperature_data:
        
        if temperature_data["temperature_values"][-1] > triggerMaxTemp  :
            erroMaxTemp+=1
        elif temperature_data["temperature_values"][-1] < triggerMinTemp  :
            erroMinTemp+=1
        else:
            valorDentroLimiteTemp+=1
            
    if luminosity_data:
        
        if luminosity_data["luminosity_values"][-1] > triggerMaxLum  :
            erroMaxLum+=1
        elif luminosity_data["luminosity_values"][-1] < triggerMinLum  :
            erroMinLum+=1
        else:
            valorDentroLimiteLum+=1
    
    return luminosity_data, temperature_data


#update line graphs
@app.callback(
    Output('luminosity-graph', 'figure'),
    Output('temperature-graph', 'figure'),
    #add one output for umidity
    Input('luminosity-data-store', 'data'),
    Input('temperature-data-store', 'data')
    #add one input for temperature
)
def update_graph(luminosity_data, temperature_data):
    fig_luminosity = generic_update_graph(luminosity_data,"luminosity","Luminosidade","orange")
    fig_temperature = generic_update_graph(temperature_data,"temperature","Temperatura","red")
    #add umidity things
    
    return fig_luminosity, fig_temperature


@app.callback(
    Output('luminosity-ErrorData-graph','figure'),
    Output('temperature-ErrorData-graph','figure'),

    Input('temperature-data-store', 'data')  # Ou outra entrada que faça sentido

)
def updateErroGraph(temperatureData):
        luminosity_histogram = generic_updateErroGraph([valorDentroLimiteLum,erroMaxLum,erroMinLum])
        temperature_histogram = generic_updateErroGraph([valorDentroLimiteTemp,erroMaxTemp,erroMinTemp])
        return luminosity_histogram,temperature_histogram


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
            xaxis_title='Categoria de Temperatura',
            yaxis_title='Quantidade',
            yaxis=dict(title='Quantidade', autorange=True)  # Autoresiza o range do eixo Y
        )

        return fig_histogram



    
###########################################################################################################################
#Run server
if __name__ == '__main__':
    app.run_server(debug=True, host=DASH_HOST, port=8050)
    

