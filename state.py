import os
import json

STATE_PATH = 'state.json'

class PersistentState:
  def __init__(self):
    self.state = {
      'lastTimestamp': 1642951192000,
      'lockedSupply': 0,
      'lockedSupplyValidity': 1650398706
    }

    if os.path.exists(STATE_PATH):
      with open(STATE_PATH) as fp:
        self.state = json.load(fp)
    else:
      self.save()

  def update(self, key, value):
    self.state[key] = value
    self.save()
    
  def save(self):
    with open(STATE_PATH, 'w') as fp:
      json.dump(self.state, fp)