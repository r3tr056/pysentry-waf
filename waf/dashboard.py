import dash
import dash_core_components as dcc
import dash_html_components as html
from request import DBController
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_Table
from dash.dependencies import Input, Output
import numpy as np

from flask import Flask, render_template
import json

possible_attacks = ['sqli', 'xss', 'cmdi', 'path-traversal', 'valid', 'parameter-tampering']

def generate_figure(df):
	fig = make_subplots(rows = 1, cols = 3, specs=[[]])