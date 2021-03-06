# using some of the code from https://github.com/EthanMacdonald/h-DQN/blob/master/agent/hDQN.py

import numpy as np
import matplotlib.pyplot as plt
from collections import namedtuple
from envs.gridworld_relational1 import Gridworld
from agent.agent import hDQN
from keras.models import Sequential
from keras.layers import Dense, Activation
from keras.optimizers import SGD, RMSprop
from pdb import set_trace 

plt.style.use('ggplot')

def init():
    # TRAIN HRL PARAMS
    num_thousands = 1
    num_epis = 10000


    # GRID WORLD GEOMETRICAL PARAMETERS
    n_dim = 5 # pick odd numbers
    start = np.zeros((1,2),dtype=int)
    start[0,0] = 0
    start[0,1] = 1
    n_obj = 3
    min_num = 1
    max_num = 30

    # EXTRINSIC REWARDS
    not_moving_reward = -1
    game_over_reward = -100
    step_reward = -1
    current_goal_reward = 500
    final_goal_reward = 10000

    # INTRINSIC REWARDS
    intrinsic_goal_reward = 100
    intrinsic_step_reward = -1
    intrinsic_wrong_goal_reward = -10

    # create and initialize the environment   
    env = Gridworld(n_dim, 
                    start, 
                    n_obj, 
                    min_num, 
                    max_num,
                    not_moving_reward, 
                    game_over_reward, 
                    step_reward, 
                    current_goal_reward, 
                    final_goal_reward,
                    intrinsic_goal_reward, 
                    intrinsic_step_reward, 
                    intrinsic_wrong_goal_reward)


    # PARAMETERS OF MEATA CONTROLLER
    meta_input_dim = 2 + n_dim**2
    meta_nodes = [40, n_obj]
    meta_layers = [Dense] * 2
    meta_inits = ['lecun_uniform'] * 2
    meta_activations = ['relu'] * 1 + ['softmax']
    meta_loss = "mean_squared_error"
    meta_optimizer=RMSprop(lr=0.00025, rho=0.9, epsilon=1e-06)
    meta_batch_size = 1000
    meta_epsilon = 1.0

    # PARAMETERS OF THE CONTROLLER
    input_dim = 2 + 1 + n_dim**2
    n_moves = 4
    nodes = [40, n_moves] 
    layers = [Dense] * 2
    inits = ['lecun_uniform'] * 2
    activations = ['relu'] * 1 + ['softmax']
    loss = "mean_squared_error"
    optimizer=RMSprop(lr=0.00025, rho=0.9, epsilon=1e-06)
    batch_size = 100
    gamma = 0.975
    epsilon = 1.0
    tau = 0.001

    # create and initialize the agent
    agent = hDQN(env=env, 
                meta_layers=meta_layers, 
                meta_inits=meta_inits,
                meta_nodes=meta_nodes, 
                meta_activations=meta_activations,
                meta_input_dim = meta_input_dim,
                meta_loss=meta_loss, 
                meta_optimizer=meta_optimizer,
                layers=layers, 
                inits=inits, 
                nodes=nodes,
                activations=activations, 
                input_dim = input_dim,
                loss=loss,
                optimizer=optimizer,
                batch_size=batch_size,
                meta_batch_size=meta_batch_size, 
                gamma=gamma,
                meta_epsilon=meta_epsilon, 
                epsilon=epsilon, 
                tau = tau)

    return env, agent, num_thousands, num_epis

def train_HRL(env, agent, num_thousands=12, num_epis=10):

    controllerExperience = namedtuple("controllerExperience", 
        ["agent_state", "goal", "action", "reward", "next_agent_state", "done"])
    MetaExperience = namedtuple("MetaExperience",   
        ["agent_state", "goal", "reward", "next_agent_state", "done"])

    visits = np.zeros((num_thousands, env.n_dim, env.n_dim))
    anneal_factor = (1.0-0.1)/(num_thousands * num_epis)
    print("Annealing factor: " + str(anneal_factor))
    game_won_counter = 0
    game_over_counter = 0
    game_result_history = []
    for episode_thousand in range(num_thousands):
        for episode in range(num_epis):
            print("\n\n\n\n### EPISODE "  + str(episode_thousand*num_thousands + episode) + "###")
            agent_state = env.reset() # the returned agent_state is just a (2,) numpy array 
            visits[episode_thousand, agent_state[0,0], agent_state[0,1]] += 1
            terminal = False
            while not terminal:  # this loop is for meta-controller, while state not terminal
                goal_idx, goal = agent.select_goal(agent_state)  # meta controller selects a goal
                agent.goal_selected[goal_idx] += 1
                print("\nNew Goal: "  + str(goal) + "\nState-Actions: ")
                total_extrinsic_reward = 0
                s0_agent = agent_state
                selected_goal_reached = False
                while not terminal and not selected_goal_reached: # this loop is for meta, while state not terminal
                    action_idx, action = agent.select_action(agent_state, goal, goal_idx) # controller selects an action among permitable actions
                    # print(str((state,action)) + "; ")
                    extrinsic_reward, next_agent_state = env.take_action(action_idx) # RIGHT NOW THE DONE IS NOT IMPLEMENTED YET 
                    visits[episode_thousand, next_agent_state[0,0], next_agent_state[0,1]] += 1
                    intrinsic_reward, selected_goal_reached = env.intrinsic_critique(next_agent_state, goal)

                    print ("action ----> "  + action)
                    print ("state after action ----> " + "[" + str(next_agent_state[0,0]) +", " + 
                            str(next_agent_state[0,1]) + "]" )
                    print ("---------------------")

                    terminal = env.is_terminal(next_agent_state)[0] or env.is_terminal(next_agent_state)[1]
                    object_reached = env.grid_mat[next_agent_state[0,0], next_agent_state[0,1]]
                    if selected_goal_reached:
                        agent.goal_success[goal_idx] += 1
                        print("SELECTED GOAL REACHED! ")
                        print("the object reached which should equal the selected goal: " + str(object_reached))
                        print ("original objects: {}".format(env.original_objects))
                        print ("********************")
                    if env.is_terminal(next_agent_state)[0]:
                        game_over_counter += 1
                        game_result_history.append("game over")
                        print("GAME OVER!!!") 
                        print("selected goal:" + str(goal))
                        print("the object reached: " +  str(object_reached))
                        print("the current target goal: " + str(env.current_target_goal))
                        print ("original objects: {}".format(env.original_objects))                        
                        print("********************")
                    if env.is_terminal(next_agent_state)[1]:
                        game_won_counter += 1
                        game_result_history.append("game over")
                        print("GAME WON!!!") 
                        print("the object reached: " +  str(object_reached))
                        print("the current target goal: " + str(env.current_target_goal))
                        print ("original objects: {}".format(env.original_objects))                        
                        print("********************")


                    # if env.grid_mat[next_agent_state[0], next_agent_state[1]] == env.original_objects[-1]:
                    #     print("final object/number picked!! ")
                    exp = controllerExperience(agent_state, goal, action_idx, intrinsic_reward, 
                        next_agent_state, selected_goal_reached)
                    agent.store(exp, meta=False)
                    agent.update(meta=False)
                    agent.update(meta=True)
                    total_extrinsic_reward += extrinsic_reward
                    agent_state = next_agent_state
                exp = MetaExperience(s0_agent, goal, total_extrinsic_reward, agent_state, terminal)
                agent.store(exp, meta=True)
                # set_trace()

                #Annealing 
                agent.meta_epsilon -= anneal_factor
                agent.epsilon -= anneal_factor
                # avg_success_rate = agent.goal_success[goal_idx] / agent.goal_selected[goal_idx]

                # if(avg_success_rate == 0 or avg_success_rate == 1):
                #     agent.epsilon -= anneal_factor
                # else:
                #     agent.epsilon = 1 - avg_success_rate
            
                if(agent.epsilon < 0.1):
                    agent.epsilon = 0.1


            print("meta_epsilon: " + str(agent.meta_epsilon))
            print("epsilon: " + str(agent.epsilon))

    with open("logs/logs.txt", "w") as file:
        file.write("game_won_counter: {}\n".format(game_won_counter)) 
        file.write("game_over_counter: {}\n".format(game_over_counter))

    with open("logs/game_result_history.txt", "w") as file:
        for game in game_result_history:
            # item = game + "\n"
            item = game + "\n"
            file.write(item)

    print ("SAVING THE MODELS .............")  
    # serialize model to JSON
    model_json = agent.meta_controller.to_json()
    with open("saved_models/meta_controller.json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    agent.meta_controller.save_weights("meta_controller.h5")
    print("Saved model to disk")

    # serialize model to JSON
    model_json = agent.target_meta_controller.to_json()
    with open("saved_models/target_meta_controller.json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    agent.target_meta_controller.save_weights("target_meta_controller.h5")
    print("Saved model to disk")

    # serialize model to JSON
    model_json = agent.controller.to_json()
    with open("saved_models/controller.json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    agent.controller.save_weights("controller.h5")
    print("Saved model to disk")

    # serialize model to JSON
    model_json = agent.target_controller.to_json()
    with open("saved_models/target_controller.json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    agent.meta_controller.save_weights("target_controller.h5")
    print("Saved model to disk")


def train_controller(env, agent):

    controllerExperience = namedtuple("controllerExperience", 
        ["agent_state", "goal", "action", "reward", "next_agent_state", "done"])
    num_epis = 1000
    anneal_factor = (1.0-0.1)/(num_epis)
    print("Annealing factor: " + str(anneal_factor))
    for episode in range(num_epis):
        print("\n\n### EPISODE "  + str(episode) + "###")
        agent_state = env.reset() # the returned agent_state is just a (2,) numpy array 

        terminal = False
        while not terminal:  # this loop is for meta-controller, while state not terminal
            goal_idx, goal = agent.select_goal(agent_state)  # meta controller selects a goal
            agent.goal_selected[goal_idx] += 1
            print("\nNew Goal: "  + str(goal) + "\nState-Actions: ")
            s0_agent = agent_state
            selected_goal_reached = False
            while not terminal and not selected_goal_reached:
                action_idx, action = agent.select_action(agent_state, goal, goal_idx) # controller selects an action among permitable actions
                # print(str((state,action)) + "; ")
                extrinsic_reward, next_agent_state = env.take_action(action_idx) # RIGHT NOW THE DONE IS NOT IMPLEMENTED YET 
                intrinsic_reward, selected_goal_reached = env.intrinsic_critique(next_agent_state, goal)


                print ("action ----> "  + action)
                print ("state after action ----> " + "[" + str(next_agent_state[0,0]) +", " + 
                        str(next_agent_state[0,1]) + "]" )
                print ("---------------------")

                terminal = env.is_terminal(next_agent_state)[0] or env.is_terminal(next_agent_state)[1]
                object_reached = env.grid_mat[next_agent_state[0,0], next_agent_state[0,1]]
                if selected_goal_reached:
                    agent.goal_success[goal_idx] += 1
                    print("SELECTED GOAL REACHED! ")
                    print("the object reached which should equal the selected goal: " + str(object_reached))
                    print ("original objects: {}".format(env.original_objects))
                    print ("********************")
                if env.is_terminal(next_agent_state)[0]:
                    print("GAME OVER!!!") 
                    print("selected goal:" + str(goal))
                    print("the object reached: " +  str(object_reached))
                    print("the current target goal: " + str(env.current_target_goal))
                    print ("original objects: {}".format(env.original_objects))                        
                    print("********************")
                if env.is_terminal(next_agent_state)[1]:
                    print("GAME WON!!!") 
                    print("the object reached: " +  str(object_reached))
                    print("the current target goal: " + str(env.current_target_goal))
                    print ("original objects: {}".format(env.original_objects))                        
                    print("********************")
                
                exp = controllerExperience(agent_state, goal, action_idx, intrinsic_reward, 
                                            next_agent_state, selected_goal_reached)
                agent.store(exp, meta=False)
                agent.update(meta=False)
                agent_state = next_agent_state
        

        #Annealing, just anneal the controller epsilon
        avg_success_rate = agent.goal_success[goal_idx] / agent.goal_selected[goal_idx]
        annealgent.epsilon -= anneal_factor
        
        # if(avg_success_rate == 0 or avg_success_rate == 1):
        #     agent.epsilon -= anneal_factor
        # else:
        #     agent.epsilon = 1- avg_success_rate
    
        # if(agent.epsilon < 0.1):
        #     agent.epsilon = 0.1
        print("epsilon: " + str(agent.epsilon))

    
    # SAVING MODELS AND THEIR WEIGHTS
    # serialize model to JSON
    model_json = agent.controller.to_json()
    with open("saved_models/controller.json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    agent.controller.save_weights("controller.h5")
    print("Saved model to disk")

    # serialize model to JSON
    model_json = agent.target_controller.to_json()
    with open("saved_models/target_controller.json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    agent.meta_controller.save_weights("target_controller.h5")
    print("Saved model to disk")



def main():

    env, agent, num_thousands, num_epis = init()
    train_HRL(env, agent, num_thousands, num_epis)
    # set_trace()
    # train_controller(env, agent)
    
            
    # eps = list(range(1,13))
    # plt.subplot(2, 3, 1)
    # plt.plot(eps, visits[:,0]/1000)
    # plt.xlabel("Episodes (*1000)")
    # plt.ylim(-0.01, 2.0)
    # plt.xlim(1, 12)
    # plt.title("S1")
    # plt.grid(True)

    # plt.subplot(2, 3, 2)
    # plt.plot(eps, visits[:,1]/1000)
    # plt.xlabel("Episodes (*1000)")
    # plt.ylim(-0.01, 2.0)
    # plt.xlim(1, 12)
    # plt.title("S2")
    # plt.grid(True)

    # plt.subplot(2, 3, 3)
    # plt.plot(eps, visits[:,2]/1000)
    # plt.xlabel("Episodes (*1000)")
    # plt.ylim(-0.01, 2.0)
    # plt.xlim(1, 12)
    # plt.title("S3")
    # plt.grid(True)

    # plt.subplot(2, 3, 4)
    # plt.plot(eps, visits[:,3]/1000)
    # plt.xlabel("Episodes (*1000)")
    # plt.ylim(-0.01, 2.0)
    # plt.xlim(1, 12)
    # plt.title("S4")
    # plt.grid(True)

    # plt.subplot(2, 3, 5)
    # plt.plot(eps, visits[:,4]/1000)
    # plt.xlabel("Episodes (*1000)")
    # plt.ylim(-0.01, 2.0)
    # plt.xlim(1, 12)
    # plt.title("S5")
    # plt.grid(True)

    # plt.subplot(2, 3, 6)
    # plt.plot(eps, visits[:,5]/1000)
    # plt.xlabel("Episodes (*1000)")
    # plt.ylim(-0.01, 2.0)
    # plt.xlim(1, 12)
    # plt.title("S6")
    # plt.grid(True)
    # plt.savefig('first_run.png')
    # plt.show()

if __name__ == "__main__":
    main()