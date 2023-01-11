# Pyomo AbstractModel for the Electric Veichles Shortest Path Problem
# ATTENTION: Invalid or not existing arcs are has to be set to the invalid 
# state -1, those arcs will not be considered in the model.
from pprint import pprint
import re
from pyomo.environ import *
from pyomo.opt import SolverFactory, TerminationCondition


def obj_rule(model):
    travel_time = sum(model.x[i,j] * model.arc_time[i,j] for j in model.nodes for i in model.nodes if model.arc_time[i,j] != -1)
    charging_time = sum(model.r[i] for i in model.nodes)
    return travel_time + charging_time


def node_flow_rule(model, v):
    outgoing_arcs = sum(model.x[v,i] for i in model.nodes if model.arc_time[v,i] != -1)
    incoming_arcs = sum(model.x[i,v] for i in model.nodes if model.arc_time[i,v] != -1)
    if v == model.start_node:
        return outgoing_arcs - incoming_arcs == 1
    elif v == model.end_node:
        return outgoing_arcs - incoming_arcs == -1
    else:
        return outgoing_arcs - incoming_arcs == 0


def node_visit_rule(model, v):
    if v == model.start_node or v == model.end_node:
        return Constraint.Skip
    else:
        incoming_arcs = sum(model.x[i,v] for i in model.nodes if model.arc_time[i,v] != -1)
        return model.y[v] == incoming_arcs


def min_charge_time_rule(model, v):
    if v == model.start_node or v == model.end_node:
        return Constraint.Skip
    else:
        return model.min_charge_time * model.y[v] <= model.r[v]


def max_charge_time_rule(model, v):
    if v == model.start_node or v == model.end_node:
        return Constraint.Skip
    else:
        return model.r[v] <= model.max_charge_time * model.y[v]


def starting_battery_rule(model, v):
    if v == model.start_node:
        return model.C_out[v] == model.start_capacity
    else:
        return Constraint.Skip


def battery_charging_rule(model, v):
    if v == model.start_node or v == model.end_node:
        return Constraint.Skip
    else:
        return model.C_out[v] == model.C_in[v] + model.r[v] * model.charger_power[v]


def min_in_battery_rule(model, v):
    if v == model.start_node:
        return Constraint.Skip
    else:
        return model.min_capacity * model.y[v] <= model.C_in[v]


def max_in_battery_rule(model, v):
    if v == model.start_node:
        return Constraint.Skip
    else:
        return model.C_in[v] <= model.max_capacity * model.y[v]


def min_out_battery_rule(model, v):
    if v == model.end_node:
        return Constraint.Skip
    else:
        return model.min_capacity * model.y[v] <= model.C_out[v]


def max_out_battery_rule(model, v):
    if v == model.end_node:
        return Constraint.Skip
    else:
        return model.C_out[v] <= model.max_capacity * model.y[v]


def battery_consumption1_rule(model, i, j):
    M_1 = model.max_capacity + model.car_efficiency * model.arc_distance[i,j]
    return model.C_in[j] <= model.C_out[i] - model.car_efficiency * model.arc_distance[i,j] + M_1 * (1 - model.x[i,j])


def battery_consumption2_rule(model, i, j):
    M_2 = model.max_capacity - model.car_efficiency * model.arc_distance[i,j]
    return model.C_in[j] >= model.C_out[i] - model.car_efficiency * model.arc_distance[i,j] - M_2 * (1 - model.x[i,j])


def buildmodel():
    # Model
    model = AbstractModel()
    # Sets
    model.nodes = Set()
    # Params
    model.start_node = Param()
    model.end_node = Param()
    model.max_capacity = Param()
    model.min_capacity = Param()
    model.start_capacity = Param()
    model.car_efficiency = Param()
    model.max_charge_time = Param()
    model.min_charge_time = Param()
    model.charger_power = Param(model.nodes)
    model.arc_time = Param(model.nodes, model.nodes)
    model.arc_distance = Param(model.nodes, model.nodes)
    # Variables
    model.x = Var(model.nodes, model.nodes, domain = Binary)
    model.y = Var(model.nodes, domain = Binary)
    model.r = Var(model.nodes, domain = NonNegativeReals)
    model.C_in = Var(model.nodes, domain = NonNegativeReals)
    model.C_out = Var(model.nodes, domain = NonNegativeReals)
    # Objective
    model.obj = Objective(rule = obj_rule, sense = minimize)
    # Constraints
    model.node_flow_constraint = Constraint(model.nodes, rule = node_flow_rule)
    model.node_visit_constraint = Constraint(model.nodes, rule = node_visit_rule)
    model.min_charge_time_constraint = Constraint(model.nodes, rule = min_charge_time_rule)
    model.max_charge_time_constraint = Constraint(model.nodes, rule = max_charge_time_rule)
    model.starting_battery_constraint = Constraint(model.nodes, rule = starting_battery_rule)
    model.battery_charging_constraint = Constraint(model.nodes, rule = battery_charging_rule)
    model.min_in_battery_constraint = Constraint(model.nodes, rule = min_in_battery_rule)
    model.max_in_battery_constraint = Constraint(model.nodes, rule = max_in_battery_rule)
    model.min_out_battery_constraint = Constraint(model.nodes, rule = min_out_battery_rule)
    model.max_out_battery_constraint = Constraint(model.nodes, rule = max_out_battery_rule)
    model.battery_consumption1_constraint = Constraint(model.nodes, model.nodes, rule = battery_consumption1_rule)
    model.battery_consumption2_constraint = Constraint(model.nodes, model.nodes, rule = battery_consumption2_rule)
    return model


# optimize function instantiates an AbstractModel from an AMPL format given file, applies a solver
# to the instance and then returns the solutions to the caller.
def optimize(ampl_file):
    model = buildmodel()
    instance = model.create_instance(ampl_file)
    opt = SolverFactory('cplex_persistent')

    opt.options['mip_tolerances_mipgap'] = 0
    opt.options['mip_interval'] = -1

    """opt.options['simplex_tolerances_optimality'] = 1e-9
    opt.options['mip_tolerances_mipgap'] = 0e-9
    opt.options['mip_tolerances_absmipgap'] = 0e-9"""
    
    opt.set_instance(instance)
    results = opt.solve(tee = True)
    print(results)
    if results.solver.termination_condition == TerminationCondition.optimal:
        print('Path:')
        for i in instance.x:
            if value(instance.x[i]) != 0:
                print('\tx[{}]={}'.format(i, value(instance.x[i])))
        print('Charging stops:')
        for i in instance.r:
            if value(instance.r[i]) != 0:
                print('\tr[{}]={}'.format(i, value(instance.r[i])))