from bots.botsconfig import *
from edifact import syntax
from recordsD96AUN import recorddefs


structure = [
{ID: 'UNH', MIN: 1, MAX: 1, LEVEL: [
    {ID: 'BGM', MIN: 1, MAX: 1},
    {ID: 'DTM', MIN: 1, MAX: 35},
    {ID: 'ALI', MIN: 0, MAX: 5},
    {ID: 'FTX', MIN: 0, MAX: 99},
    {ID: 'RFF', MIN: 0, MAX: 99, LEVEL: [
        {ID: 'DTM', MIN: 0, MAX: 5},
    ]},
    {ID: 'NAD', MIN: 0, MAX: 99, LEVEL: [
        {ID: 'LOC', MIN: 0, MAX: 25},
        {ID: 'RFF', MIN: 0, MAX: 10, LEVEL: [
            {ID: 'DTM', MIN: 0, MAX: 5},
        ]},
        {ID: 'CTA', MIN: 0, MAX: 5, LEVEL: [
            {ID: 'COM', MIN: 0, MAX: 5},
        ]},
    ]},
    {ID: 'TAX', MIN: 0, MAX: 5, LEVEL: [
        {ID: 'MOA', MIN: 0, MAX: 1},
    ]},
    {ID: 'CUX', MIN: 0, MAX: 5, LEVEL: [
        {ID: 'DTM', MIN: 0, MAX: 5},
    ]},
    {ID: 'PAT', MIN: 0, MAX: 10, LEVEL: [
        {ID: 'DTM', MIN: 0, MAX: 5},
        {ID: 'PCD', MIN: 0, MAX: 1},
        {ID: 'MOA', MIN: 0, MAX: 1},
    ]},
    {ID: 'TDT', MIN: 0, MAX: 10, LEVEL: [
        {ID: 'LOC', MIN: 0, MAX: 10},
    ]},
    {ID: 'TOD', MIN: 0, MAX: 5, LEVEL: [
        {ID: 'LOC', MIN: 0, MAX: 2},
    ]},
    {ID: 'ALC', MIN: 0, MAX: 10, LEVEL: [
        {ID: 'ALI', MIN: 0, MAX: 5},
        {ID: 'DTM', MIN: 0, MAX: 9},
        {ID: 'QTY', MIN: 0, MAX: 1, LEVEL: [
            {ID: 'RNG', MIN: 0, MAX: 1},
        ]},
        {ID: 'PCD', MIN: 0, MAX: 1, LEVEL: [
            {ID: 'RNG', MIN: 0, MAX: 1},
        ]},
        {ID: 'MOA', MIN: 0, MAX: 2, LEVEL: [
            {ID: 'RNG', MIN: 0, MAX: 1},
        ]},
        {ID: 'RTE', MIN: 0, MAX: 1, LEVEL: [
            {ID: 'RNG', MIN: 0, MAX: 1},
        ]},
        {ID: 'TAX', MIN: 0, MAX: 5, LEVEL: [
            {ID: 'MOA', MIN: 0, MAX: 1},
        ]},
    ]},
    {ID: 'PGI', MIN: 0, MAX: 1000, LEVEL: [
        {ID: 'DTM', MIN: 0, MAX: 15},
        {ID: 'QTY', MIN: 0, MAX: 10},
        {ID: 'ALI', MIN: 0, MAX: 5},
        {ID: 'FTX', MIN: 0, MAX: 5},
        {ID: 'CUX', MIN: 0, MAX: 10, LEVEL: [
            {ID: 'DTM', MIN: 0, MAX: 5},
        ]},
        {ID: 'PRI', MIN: 0, MAX: 100, LEVEL: [
            {ID: 'CUX', MIN: 0, MAX: 1},
            {ID: 'APR', MIN: 0, MAX: 1},
            {ID: 'RNG', MIN: 0, MAX: 1},
            {ID: 'DTM', MIN: 0, MAX: 5},
        ]},
        {ID: 'TAX', MIN: 0, MAX: 10, LEVEL: [
            {ID: 'MOA', MIN: 0, MAX: 1},
        ]},
        {ID: 'ALC', MIN: 0, MAX: 99, LEVEL: [
            {ID: 'ALI', MIN: 0, MAX: 5},
            {ID: 'QTY', MIN: 0, MAX: 1, LEVEL: [
                {ID: 'RNG', MIN: 0, MAX: 1},
            ]},
            {ID: 'PCD', MIN: 0, MAX: 1, LEVEL: [
                {ID: 'RNG', MIN: 0, MAX: 1},
            ]},
            {ID: 'MOA', MIN: 0, MAX: 2, LEVEL: [
                {ID: 'RNG', MIN: 0, MAX: 1},
            ]},
            {ID: 'RTE', MIN: 0, MAX: 1, LEVEL: [
                {ID: 'RNG', MIN: 0, MAX: 1},
            ]},
            {ID: 'TAX', MIN: 0, MAX: 5, LEVEL: [
                {ID: 'MOA', MIN: 0, MAX: 1},
            ]},
        ]},
        {ID: 'NAD', MIN: 0, MAX: 20, LEVEL: [
            {ID: 'LOC', MIN: 0, MAX: 5},
            {ID: 'RFF', MIN: 0, MAX: 10, LEVEL: [
                {ID: 'DTM', MIN: 0, MAX: 5},
            ]},
            {ID: 'CTA', MIN: 0, MAX: 5, LEVEL: [
                {ID: 'COM', MIN: 0, MAX: 5},
            ]},
        ]},
        {ID: 'PAT', MIN: 0, MAX: 10, LEVEL: [
            {ID: 'DTM', MIN: 0, MAX: 5},
            {ID: 'PCD', MIN: 0, MAX: 1},
            {ID: 'MOA', MIN: 0, MAX: 1},
        ]},
        {ID: 'TDT', MIN: 0, MAX: 10, LEVEL: [
            {ID: 'LOC', MIN: 0, MAX: 10},
        ]},
        {ID: 'TOD', MIN: 0, MAX: 5, LEVEL: [
            {ID: 'LOC', MIN: 0, MAX: 2},
        ]},
        {ID: 'PAC', MIN: 0, MAX: 10, LEVEL: [
            {ID: 'MEA', MIN: 0, MAX: 10},
            {ID: 'HAN', MIN: 0, MAX: 5},
        ]},
        {ID: 'LIN', MIN: 0, MAX: 999999, LEVEL: [
            {ID: 'PIA', MIN: 0, MAX: 10},
            {ID: 'IMD', MIN: 0, MAX: 999},
            {ID: 'MEA', MIN: 0, MAX: 10},
            {ID: 'QTY', MIN: 0, MAX: 10},
            {ID: 'HAN', MIN: 0, MAX: 5},
            {ID: 'ALI', MIN: 0, MAX: 5},
            {ID: 'DTM', MIN: 0, MAX: 10},
            {ID: 'NAD', MIN: 0, MAX: 99},
            {ID: 'RFF', MIN: 0, MAX: 1},
            {ID: 'LOC', MIN: 0, MAX: 1},
            {ID: 'DOC', MIN: 0, MAX: 1},
            {ID: 'FTX', MIN: 0, MAX: 5},
            {ID: 'CCI', MIN: 0, MAX: 999, LEVEL: [
                {ID: 'CAV', MIN: 0, MAX: 10},
                {ID: 'MEA', MIN: 0, MAX: 10},
            ]},
            {ID: 'TAX', MIN: 0, MAX: 10, LEVEL: [
                {ID: 'MOA', MIN: 0, MAX: 1},
            ]},
            {ID: 'CUX', MIN: 0, MAX: 5, LEVEL: [
                {ID: 'DTM', MIN: 0, MAX: 5},
            ]},
            {ID: 'PRI', MIN: 0, MAX: 100, LEVEL: [
                {ID: 'CUX', MIN: 0, MAX: 1},
                {ID: 'APR', MIN: 0, MAX: 1},
                {ID: 'RNG', MIN: 0, MAX: 1},
                {ID: 'DTM', MIN: 0, MAX: 5},
                {ID: 'PCD', MIN: 0, MAX: 5},
            ]},
            {ID: 'ALC', MIN: 0, MAX: 99, LEVEL: [
                {ID: 'ALI', MIN: 0, MAX: 5},
                {ID: 'DTM', MIN: 0, MAX: 9},
                {ID: 'QTY', MIN: 0, MAX: 1, LEVEL: [
                    {ID: 'RNG', MIN: 0, MAX: 1},
                ]},
                {ID: 'PCD', MIN: 0, MAX: 1, LEVEL: [
                    {ID: 'RNG', MIN: 0, MAX: 1},
                ]},
                {ID: 'MOA', MIN: 0, MAX: 2, LEVEL: [
                    {ID: 'RNG', MIN: 0, MAX: 1},
                ]},
                {ID: 'RTE', MIN: 0, MAX: 1, LEVEL: [
                    {ID: 'RNG', MIN: 0, MAX: 1},
                ]},
                {ID: 'TAX', MIN: 0, MAX: 5, LEVEL: [
                    {ID: 'MOA', MIN: 0, MAX: 1},
                ]},
            ]},
            {ID: 'PAC', MIN: 0, MAX: 10, LEVEL: [
                {ID: 'MEA', MIN: 0, MAX: 10},
                {ID: 'HAN', MIN: 0, MAX: 5},
            ]},
            {ID: 'PAT', MIN: 0, MAX: 10, LEVEL: [
                {ID: 'DTM', MIN: 0, MAX: 5},
                {ID: 'PCD', MIN: 0, MAX: 1},
                {ID: 'MOA', MIN: 0, MAX: 1},
            ]},
            {ID: 'TDT', MIN: 0, MAX: 10, LEVEL: [
                {ID: 'LOC', MIN: 0, MAX: 10},
            ]},
            {ID: 'TOD', MIN: 0, MAX: 5, LEVEL: [
                {ID: 'LOC', MIN: 0, MAX: 2},
            ]},
        ]},
    ]},
    {ID: 'UNT', MIN: 1, MAX: 1},
]}
]
