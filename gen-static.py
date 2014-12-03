#!/usr/bin/env python

import json
import sqlite3

class SDE:
	def __init__(self, db):
		self.db = db

	def groups_in_category(self, category):
		c = self.db.cursor()
		c.execute("SELECT categoryID FROM invCategories WHERE categoryName = ?", (category,))
		category_id = c.fetchone()[0]

		c.execute("SELECT groupName FROM invGroups WHERE categoryID = ?", (category_id,))
		return map(lambda x: x[0], c.fetchall())

	def group_id(self, group):
		c = self.db.cursor()
		c.execute("SELECT groupID FROM invGroups WHERE groupName = ?", (group,))
		return c.fetchone()[0]

	def items_in_group(self, group):
		group_id = self.group_id(group)

		# dirty hack here - some of the QA towers are marked published, so
		# filter them by name instead of published field.
		c = self.db.cursor()
		c.execute("""SELECT typeName FROM invTypes WHERE groupID = ?
				  AND typeName NOT LIKE 'QA %' AND published = 1""", (group_id,))
		return map(lambda x: x[0], c.fetchall())

	def item_attribute(self, item_name, attribute_name):
		c = self.db.cursor()
		c.execute("SELECT typeID FROM invTypes WHERE typeName = ?", (item_name,))
		item_id = c.fetchone()[0]

		c.execute("SELECT attributeID FROM dgmAttributeTypes WHERE attributeName = ?", (attribute_name,))
		attribute_id = c.fetchone()[0]


		c.execute("SELECT valueInt, valueFloat FROM dgmTypeAttributes WHERE typeID = ? AND attributeID = ?",
				  (item_id, attribute_id))
		values = c.fetchone()
		if not values:
			return None
		return values[0] or values[1]

	def item_volume(self, item_name):
		c = self.db.cursor()
		c.execute("SELECT volume FROM invTypes WHERE typeName = ?", (item_name,))
		return c.fetchone()[0]

def bonused_weapon_type(sde, tower_type):
	def hasbonus(name):
		return sde.item_attribute(tower_type, 'controlTower%sBonus' % name)
	if hasbonus('LaserDamage') or hasbonus('LaserOptimal'):
		return 'energy'
	if hasbonus('MissileROF') or hasbonus('MissileVelocity'):
		return 'missile'
	if hasbonus('HybridDamage') or hasbonus('HybridOptimal'):
		return 'hybrid'
	if hasbonus('ProjectileROF') or hasbonus('ProjectileFalloff') or hasbonus('ProjectileOptimal'):
		return 'projectile'
	return None

def dump_towers(sde):
	towers = []
	tower_types = sde.items_in_group('Control Tower')
	for ty in tower_types:
		t = {'name': ty}
		t['power'] = sde.item_attribute(ty, 'powerOutput')
		t['cpu'] = sde.item_attribute(ty, 'cpuOutput')
		wt = bonused_weapon_type(sde, ty)
		if wt:
			t['weapon_type'] = wt
		towers.append(t)
	return towers

def mod_weapon_type(sde, type_name):
	charge_group_id = sde.item_attribute(type_name, 'chargeGroup1')
	if charge_group_id == sde.group_id('Projectile Ammo'):
		return 'projectile'
	if charge_group_id == sde.group_id('Hybrid Charge'):
		return 'hybrid'
	if charge_group_id == sde.group_id('Frequency Crystal'):
		return 'energy'
	if charge_group_id == sde.group_id('Torpedo'):
		return 'missile'
	if charge_group_id == sde.group_id('Cruise Missile'):
		return 'missile'
	if charge_group_id == sde.group_id('Citadel Torpedo'):
		return 'missile'
	return None

def dump_mods(sde):
	mods = []
	mod_groups = sde.groups_in_category('Structure')
	# hack: control towers are themselves under the structure group but aren't
	# tower modules. We remove that group here to avoid including the towers in the module array.
	mod_groups.remove('Control Tower')
	for gr in mod_groups:
		mod_types = sde.items_in_group(gr)
		for ty in mod_types:
			t = {'name': ty}
			t['power'] = sde.item_attribute(ty, 'power') or 0
			t['cpu'] = sde.item_attribute(ty, 'cpu') or 0
			wt = mod_weapon_type(sde, ty)
			if wt:
				t['weapon_type'] = wt
			mods.append(t)
	return mods

conn = sqlite3.connect('sqlite-latest.sqlite')
sde = SDE(conn)

towers = dump_towers(sde)
mods = dump_mods(sde)

print json.dumps({'towers': towers, 'mods': mods}, indent=4, sort_keys=True)