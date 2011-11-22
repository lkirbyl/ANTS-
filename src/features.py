'''
Created on Oct 1, 2011

@author: djweiss
'''

from antpathsearch import aStarSearch
from worldstate import AIM

class FeatureExtractor:
    ''' Extracts features from ant world state for given actions.
    
    This is the template class for all feature extractors. 
    A feature extractor must implement the init_from_dict() and extract() methods.  
    '''
    
    def __init__(self, input_dict):
        ''' Create a new FeatureExtractor from a dict object.'''
        
        new_type = input_dict['_type']
        if new_type == MovingTowardsFeatures.type_name: 
            self.__class__ = MovingTowardsFeatures
        elif new_type == QualifyingFeatures.type_name:
            self.__class__ = QualifyingFeatures
        elif new_type == CompositingFeatures.type_name:
            self.__class__ = CompositingFeatures 
        else:
            raise Exception("Invalid feature class %s" + new_type)

        self.feature_names = []
        self.feature_id = {}
        
        # Call class-specific initialization.    
        self.init_from_dict(input_dict)
        
        fid = 0
        for name in self.feature_names:
            self.feature_id[name] = fid
            fid += 1

    def __str__(self):
        return str(self.__class__)
        
    def to_dict(self):
        """Convert FeatureExtractor to a human readable dict."""
        
        return {'_type': self.__class__.type_name}

    def num_features(self):
        """Size of feature vector output by this extractor."""
        
        return len(self.feature_names)
    
    def feature_name(self, fid):
        """Get the name of the fid'th feature as a string.""" 
        
        return self.feature_names[fid]
    
    def feature_id(self, name):
        """Reverse lookup the feature id of the specified feature name."""
        
        return self.feature_id[name]
       
    def init_from_dict(self, input_dict):
        """Perform any class-specific initialization, grabbing parameters from input_dict.""" 
        raise NotImplementedError
        
    def extract(self, world, state, loc, action):
        """Extracts a feature vector from a world, state, location, and action. 
        
        Feature vectors are lists of booleans, where length = num_features() regardless of 
        the # of active features.
        """
        
        raise NotImplementedError

class MovingTowardsFeatures(FeatureExtractor):
    """Very basic features.
    
    Computes three features: whether or not a given action takes an ant nearer to its closest
    enemy, food, or friendly ant.
    """
    
    type_name = 'MovingTowards'
       
    def init_from_dict(self, input_dict):
        self.feature_names.append("Moving Towards Closest Enemy")
        self.feature_names.append("Moving Towards Closest Food")
        self.feature_names.append("Moving Towards Friendly")
        self.feature_names.append("Moving Towards Closest Food on AStar path")
        #self.feature_names.append("Moving Towards Closest Enemy on AStar path")
        self.feature_names.append("Moving Towards Least Visited")

    def __init__(self):
        FeatureExtractor.__init__(self, {'_type': MovingTowardsFeatures.type_name})    
                
    def moving_towards(self, world, loc1, loc2, target):
        """Returns true if loc2 is closer to target than loc1 in manhattan distance."""
        
        return world.manhattan_distance(loc1, target) - world.manhattan_distance(loc2, target) > 0

    def moving_towards_on_astar(self, world, loc, new_loc, path_dict, target, state):
        """ Returns true, if the new_loc is the next step to go towards the target on an aStar Path. """
        if len(path_dict[loc]) != 0:
            # Is the path a path to the target and if so: does the action move the ant closer to it?
            return path_dict[loc][0] == new_loc and path_dict[loc][-1] == target
        else:
            # Check if we allow more a* searches. 60 should be doable without timeout.
            if state.a_star_counter <= 60:
                state.a_star_counter += 1
                # Generate an a*-path
                pathfinder = aStarSearch(world)
                path = pathfinder.get_path(loc,target)
                if path is not None:
                    # Remove the first entry of the path, because it's just the start again
                    path_dict[loc] = path[1:]
                    return path_dict[loc][0] == new_loc
                else:
                    # Food not near enough for this ant
                    return False
            else:
                # Fall back to greedy approximation
                #return self.moving_towards(world, loc, new_loc, target)
                return False

    def find_closest(self, world, loc, points):
        """Returns the closest point to loc from the list points, or None if points is empty."""
        if len(points) == 1:
            return points[0]
        
        locs = world.sort_by_distance(loc, points)
            
        if len(locs) > 0:
            return locs[0][1]
        else:
            return None
        
    def extract(self, world, state, loc, action):
        """Extract the three simple features."""
        
        food_loc = self.find_closest(world, loc, state.lookup_nearby_food(loc))
        enemy_loc = self.find_closest(world, loc, state.lookup_nearby_enemy(loc))
        friend_loc = self.find_closest(world, loc, state.lookup_nearby_friendly(loc))

        next_loc = world.next_position(loc, action)
        world.L.debug("loc: %s, food_loc: %s, enemy_loc: %s, friendly_loc: %s" % (str(loc), str(food_loc), str(enemy_loc), str(friend_loc)))
        # Feature vector        
        f = list()

        # Moving towards enemy
        if enemy_loc is None:
            f.append(False)
        else:
            f.append(self.moving_towards(world, loc, next_loc, enemy_loc));
        
        # Moving towards food
        if food_loc is None:
            f.append(False)
        else:
            f.append(self.moving_towards(world, loc, next_loc, food_loc));
        

        # Moving towards friendly
        if friend_loc is None:
            f.append(False)
        else:
            f.append(self.moving_towards(world, loc, next_loc, friend_loc));
        
        # Moving on aStar-path towards food
        if food_loc is None:
            f.append(False)
        else:
            f.append(self.moving_towards_on_astar(world, loc, next_loc, state.paths, food_loc, state))

        # Moving on aStar-path towards an enemy
        # This is a stupid feature.
        #if enemy_loc is None:
        #    f.append(False)
        #else:
        #    f.append(self.moving_towards_on_astar(world, loc, next_loc, state.paths, enemy_loc, state))

        # Moving towards least visited, is true, if direction leads to a square, that is the least
        # visited of the all possible squares around the ant.
        other_dirs = AIM.keys()
        other_dirs.remove(action)
        if 'halt' in other_dirs:
            other_dirs.remove('halt')
        least_visited = True
        for direction in other_dirs:
            if state.get_next_visited(loc, action) > state.get_next_visited(loc, direction):
                least_visited = False
        f.append(least_visited)

        return f
    
class QualifyingFeatures(FeatureExtractor):
    """Additional qualifier-type features.
    
    This is part of the assignment for HW3. Your features in this class don't have to depend on
    the action, but instead can be functions of state or location, e.g., "1 ant left".
    
    Implemented qualifying features:
    - Enemy nearby: Is true, if there is an enemy nearby
    - Friend nearby: True if there is a friendly ant nearby
    """
    
    type_name = 'Qualifying'
    # The radius that is used to qualify as "nearby"
    nearby_distance = 5
    
    def __init__(self):
        FeatureExtractor.__init__(self, {'_type': QualifyingFeatures.type_name})
        
    def init_from_dict(self, input_dict):
        self.feature_names.append("Enemy Nearby")
        self.feature_names.append("Friend Nearby")
        self.feature_names.append("Friend close")
        self.feature_names.append("More than 100 ants")
        self.feature_names.append("Enemy is nearer to nearest food")
        self.feature_names.append("No food in Hill")
        self.feature_names.append(">=1 food in Hill")
        self.feature_names.append(">=2 food in Hill")
        self.feature_names.append(">=3 food in Hill")
        self.feature_names.append(">=4 food in Hill")
        self.feature_names.append(">=5 food in Hill")
        self.feature_names.append(">=7 food in Hill")
        self.feature_names.append(">=8 food in Hill")
        self.feature_names.append(">=9 food in Hill")
        self.feature_names.append(">=10 food in Hill")
        self.feature_names.append("No ant defending")
        self.feature_names.append(">=1 ant defending")
        self.feature_names.append(">=2 ant defending")
        self.feature_names.append(">=3 ant defending")
        self.feature_names.append(">=4 ant defending")
        self.feature_names.append(">=5 ant defending")

    def find_closest(self, world, loc, points):
        """Returns the closest point to loc from the list points, or None if points is empty."""
        if len(points) == 1:
            return points[0]
        
        locs = world.sort_by_distance(loc, points)
            
        if len(locs) > 0:
            return locs[0][1]
        else:
            return None

    def moving_towards(self, world, loc1, loc2, target):
        """Returns true if loc2 is closer to target than loc1 in manhattan distance."""
        
        return world.manhattan_distance(loc1, target) - world.manhattan_distance(loc2, target) > 0

    def nearby(self, world, antpos, target):
        """ Returns True, if the manhattan distance between antpos and target
        is smaller or equal than nearby_distance. """
        return world.manhattan_distance(antpos, target) <= QualifyingFeatures.nearby_distance

    def extract(self, world, state, loc, action):
        """ Extract the qualifying features. """
        enemy_loc = self.find_closest(world, loc, state.lookup_nearby_enemy(loc))
        friend_loc = self.find_closest(world, loc, state.lookup_nearby_friendly(loc))
        food_loc = self.find_closest(world, loc, state.lookup_nearby_food(loc))
        
        f = []
        # Enemy nearby
        if enemy_loc is None:
            f.append(False)
        else:
            f.append(self.nearby(world, loc, enemy_loc))
        # Friend nearby
        if friend_loc is None:
            f.append(False)
        else:
            f.append(self.nearby(world, loc, friend_loc))
        # Friend close
        if friend_loc is None:
            f.append(False)
        else:
            f.append(world.manhattan_distance(loc, friend_loc) <= 2)
        # more than 100 ants
        if len(world.ants) > 100:
            f.append(True)
        else:
            f.append(False)
        # Enemy is nearer to the nearest food:
        if enemy_loc is None or food_loc is None:
            f.append(False)
        else:
            f.append(self.moving_towards(world, loc, enemy_loc, food_loc))

        return f

class CompositingFeatures(FeatureExtractor):
    """Generates new features from new existing FeatureExtractors.
    
    This is part of the assignment for HW3. CompositingFeatures takes two FeatureExtractors,
    base_f and qual_f. If len(base_f) = n and len(qual_f) = m, then this extractor generates 
    n(m+1) features consisting of the original base_f features plus a copy of base_f features 
    that is multiplied by each of the qual_f features.
    
    It is important to compute the unique names of each feature to help with debugging.

    """
    
    type_name = 'Compositing'        

    def __init__(self, base_f, qual_f):
        FeatureExtractor.__init__(self, {'_type': CompositingFeatures.type_name, 
                                         'base_f' : base_f.to_dict(), 'qual_f': qual_f.to_dict()})
                             
    def init_from_dict(self, input_dict):
        self.base_f = FeatureExtractor(input_dict['base_f']) 
        self.qual_f = FeatureExtractor(input_dict['qual_f']) 

        # Compute names based on the features we've loaded    
        self.compute_feature_names()

    def to_dict(self):
        val =  FeatureExtractor.to_dict(self)
        val['base_f'] = self.base_f.to_dict()
        val['qual_f'] = self.qual_f.to_dict()
        return val
        
    def compute_feature_names(self):
        """ Compute the list of feature names from the composition of base_f and qual_f. The
        features should be organized as follows. If base_f has n features and qual_f has m features,
        then the features are indexed as follows:
        
        f[0] through f[n-1]: base_f[0] through base_f[n-1]
        f[n] through f[2n-1]: base_f[0]*qual_f[0] through base_f[n]*qual_f[0] 
        ...
        f[mn] through f[(m+1)n-1]: base_f[n-1]*qual_f[m-1] through base_f[n-1]*qual_f[m-1] 
                
        """
        self.feature_names.extend(self.base_f.feature_names)
        for base_id in range(self.base_f.num_features()):
            for qual_id in range(self.qual_f.num_features()):
                self.feature_names.append(self.base_f.feature_name(base_id) + " AND " +\
                        self.qual_f.feature_name(qual_id))
    
    def extract(self, world, state, loc, action):
        """Extracts the combination of features according to the ordering defined by compute_feature_names()."""
        f = []
        # First get the base features
        f.extend(self.base_f.extract(world, state, loc, action))
        # Now multiply every base feature with every qualifying feature
        # This is done in the same order as the names are generated.
        f.extend([i*j for i in self.base_f.extract(world, state, loc, action)\
            for j in self.qual_f.extract(world, state, loc, action)])
        # Return the feature vector
        return f
