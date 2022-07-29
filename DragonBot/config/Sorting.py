class quicksorting:
    def __init__(self):
        self.data = []
        self.left = 0
        self.right = 0


    def actual_quicksort(self, data, left, right):
        if left >= right :            
            return 
        i = left                      
        j = right
        self.left = left
        self.right = right
        self.data = data      
        key = data[left]
        while i != j:                  
            while int(data[j][1]) > int(key[1]) and i < j:   
                j -= 1
            while int(data[i][1]) <= int(key[1]) and i < j:  
                i += 1
            if i < j:                        
                data[i], data[j] = data[j], data[i] 
        data[left] = data[i]
        data[i] = key
        self.actual_quicksort(data, left, i-1)   
        self.actual_quicksort(data, i+1, right)

    def quicksort(self, data, left, right):
        self.actual_quicksort(data, left, right)
        return self.data