typedef struct _Person {
	char *name;
	unsigned int age;
} Person;

Person *person_new(char *name, unsigned int age);
void person_set_name(Person *self, char *name);
char *person_get_name(Person *self);
void person_cry(Person *self);
void person_kill(Person *self, Person *other);
